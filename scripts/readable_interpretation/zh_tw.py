"""Traditional Chinese deterministic interpretation renderer.

This layer turns structured astrology variables into native, user-facing copy.
It does not call an LLM and it must not add chart facts that were not provided
by the calculation/reducer layer.
"""

from __future__ import annotations

import re

from typing import Any

from .final_narrative_composer import FinalNarrativeComposer, FinalNarrativeSemanticInput
from .schema import ReadableInterpretation, ReadableQuestionAnswer
from .section_narrative_spec import build_section_narrative_specs


ZH_SENTENCE_ENDINGS = "。！？"
ZH_NUMERALS = {
    1: "一",
    2: "二",
    3: "三",
    4: "四",
    5: "五",
}


def zh_clause(text: Any) -> str:
    return str(text or "").strip().rstrip(ZH_SENTENCE_ENDINGS).strip()


def normalize_zh_text(text: Any) -> str:
    value = str(text or "").strip()
    replacements = {
        "。。": "。",
        "！！": "！",
        "？？": "？",
        "；；": "；",
        "。；": "；",
        "！；": "；",
        "？；": "；",
        "；。": "。",
    }
    previous = None
    while previous != value:
        previous = value
        for old, new in replacements.items():
            value = value.replace(old, new)
    return value


def zh_sentence(text: Any) -> str:
    value = normalize_zh_text(text)
    if not value:
        return ""
    if value[-1] in ZH_SENTENCE_ENDINGS:
        return value
    return f"{value}。"


def join_zh_sentences(*parts: Any) -> str:
    output: list[str] = []
    seen: set[str] = set()
    for part in parts:
        sentence = zh_sentence(part)
        if not sentence or sentence in seen:
            continue
        seen.add(sentence)
        output.append(sentence)
    return normalize_zh_text("".join(output))


FINAL_VISIBLE_COPY_REPLACEMENTS = (
    ("行動速度就容易變急，互動很快從想處理變成對抗或升溫", "一急著把問題處理好，你們就容易越講越硬，最後變成像在吵誰對誰錯"),
    ("互動速度一升高時，雙方能不能避免進入對抗", "一急著把事情說清楚時，你們能不能不要又變成爭誰對誰錯"),
    ("互動速度一升高時", "一急著把事情說清楚時"),
    ("這段關係容易在靠近速度上升溫：", "你們一急著靠近，就容易變得緊："),
    ("這段關係容易在一急著靠近就變得緊：", "你們一急著靠近，就容易變得緊："),
    ("容易在一急著靠近就變得緊", "一急著靠近就容易變得緊"),
    ("靠近速度上升溫", "一急著靠近就變得緊"),
    ("火花後面有沒有可延續的行動", "火花後面能不能真的接下去"),
    ("火花後面還要有持續行動", "火花後面還要有實際接續"),
    ("承擔變敏感", "責任感變敏感"),
    ("承擔感", "責任感"),
    ("進入對抗", "變成爭誰對誰錯"),
    ("你們之間有會互相反應的地方，但它更像一個位置，不是直接等於關係答案", "你們確實容易被彼此牽動，但這只能說明還有火花，不能代表關係已經有結果"),
    ("你們之間有會互相牽動的地方，但它更像一個入口，不是直接等於關係答案", "你們確實容易被彼此牽動，但這只能說明還有火花，不能代表關係已經有結果"),
    ("你們確實容易被彼此反應", "你們確實容易被彼此牽動"),
    ("合盤有牽動", "星盤有吸引線索"),
    ("可以當位置，但訊息要比感覺更輕", "如果真的要說一句，也只適合短而輕的訊息"),
    ("可以當入口，但訊息要比感覺更輕", "如果真的要說一句，也只適合短而輕的訊息"),
    ("可以當方式，但訊息要比感覺更輕", "如果真的要說一句，也只適合短而輕的訊息"),
    ("訊息要比感覺更輕", "訊息要短一點、輕一點"),
    ("它提醒你還想靠近，但開口方式要小於你的情緒強度", "你想靠近是可以理解的，但如果要傳訊息，只適合短短一句，不要把情緒全部放進去"),
    ("這份想靠近可以被看見，但開口要比情緒小很多", "你想靠近是可以理解的，但如果要傳訊息，只適合短短一句，不要把情緒全部放進去"),
    ("開口方式要小於你的情緒強度", "不要把情緒全部放進訊息裡"),
    ("開口要比情緒小很多", "不要把情緒全部放進訊息裡"),
    ("把行動縮小到不需要立刻定義關係的一步", "下一步要小到對方不用立刻表態"),
    ("火花可以保留，但下一步要輕，不要把吸引變成壓力測試", "有火花可以先放著，下一步只做短而輕的一件事，不逼出答案"),
    ("沉默期先看互動會不會自然出現，不要把一次主動變成壓力測試", "沉默期先看對方會不會自然出現，不要一主動就逼對方給答案"),
    ("不要把第一次主動用成壓力測試", "第一次主動不要變成逼對方給答案"),
    ("看互動能不能不升溫，而不是誰先贏回主導權", "看你們能不能越聊越平，而不是誰先把局面扳回來"),
    ("把火花落到具體、低要求、可延續的小互動", "不要只看有沒有曖昧，要看能不能變成壓力小、能接下去的小互動"),
    ("聯絡受阻時，先以界線和自我穩定為主", "如果對方已經不讓你聯絡，現在先不要繞路找他，先把自己穩住"),
    ("用穩定行動校準強烈感受，不靠猜測下結論", "對方有沒有穩定行動，不要只靠猜測下結論"),
    ("感覺越重，越要尊重界線，用可看見的行動校準判斷", "感覺越重，越要尊重界線，回頭看對方有沒有清楚行動"),
    ("小而可觀察的互動", "一件小、看得到回應的互動"),
    ("修復方向", "接下來"),
    ("小訊號", "小回應"),
    ("聯絡受阻", "聯絡被擋住"),
    ("自我穩定", "先把自己穩住"),
    ("校準", "調整"),
    ("低要求", "壓力小"),
    ("壓力測試", "逼答案"),
    ("現實逼答案關係能不能長久", "在意這段關係能不能經得起現實"),
    ("現實壓力測試關係能不能長久", "在意這段關係能不能經得起現實"),
    ("這組動力是不安把行動速度推快：越想快點安心，越容易讓對話變成壓力測試。", "你越想快點安心，越容易讓對話變成壓力測試。"),
    ("這組動力是火花推高行動衝動：越感覺有吸引，越容易想立刻測反應。", "越感覺有吸引，越容易想立刻測反應。"),
    ("這組動力是吸引放大不安：火花可能還在，但它會讓你更急著確認安全感。", "火花可能還在，但它會讓你更急著確認安全感。"),
    ("這組動力是自尊位置和安全感互相反應：越想被看見，越容易把細節讀成自己不重要。", "你越想被看見，越容易把細節讀成自己不重要。"),
    ("這組動力是不安把行動速度推快：", "你越想快點安心，越容易發生的是："),
    ("這組動力是吸引放大不安：", "你們不是沒有火花，問題是："),
    ("這組動力是火花推高行動衝動：", "越有火花，越容易發生的是："),
    ("這組動力是吸引帶來靠近感，但", "你們之間有靠近感，但"),
    ("這組動力是自尊位置和安全感互相反應：", "真正敏感的地方是："),
    ("這組動力是想說清楚碰到承擔壓力：", "你越想一次說清楚，越容易變成："),
    ("這組動力是修復意圖被行動速度帶歪：", "你本來是想修復，但太急時會變成："),
    ("這組動力是安全感需求碰到責任壓力：", "你越需要確認，對方越容易感覺到："),
    ("這組動力是衝突速度裡還有修復位置：", "這段關係不是不能談，重點是："),
    ("這組動力是強烈牽引碰到現實界線：", "這段感覺很強，但現實上要先看："),
    ("這組動力的關鍵是：", "關鍵是："),
    ("放到時機上，這組動力不適合", "放到現在的時機看，不適合"),
    ("這組動力是", "比較像是"),
    ("這組動力不適合", "現在不適合"),
    ("關係型態：", ""),
    ("判斷：", "所以這題我會這樣看："),
    ("轉折氣候：", "接下來一段時間要留意的是："),
    ("此刻建議：", "現在比較適合："),
    ("關係生存指南：", "比較有用的做法是："),
    ("對方在感情中真正需要什麼：", "他比較吃這一套："),
    ("先避開會讓他關上的方式：", "先避開這種互動："),
    ("最容易誤會的是：", "最容易誤會的地方是："),
    ("土星訊號", "壓力感"),
    ("短期時機若有火星刺激", "短期如果情緒或衝動比較強"),
    ("吸引力不是空泛好感，而是有具體相位支撐的互動反應", "你們不是只有想像中的好感，互動裡確實有會被彼此牽動的地方"),
    ("吸引力不是空泛好感，而是有具體星盤線索支持的互動反應", "你們不是只有想像中的好感，互動裡確實有會被彼此牽動的地方"),
    ("具體相位支撐", "具體星盤線索支持"),
    ("相位支撐", "星盤線索支持"),
    ("衝突相位", "衝突線索"),
    ("成長相位", "修復線索"),
    ("相位", "星盤線索"),
    ("承接度", "接不接得住"),
    ("承接量", "能接住的份量"),
    ("時機判斷", "現在的時機"),
    ("低要求、可退場", "不要求對方立刻回答、也能自然停下來"),
    ("可退場", "能自然停下來"),
    ("自然通道", "自然聯絡"),
    ("主動加碼會讓判讀失真", "主動加碼會讓你更難看清楚他的真實反應"),
    ("這個判讀會更成立", "這個方向就更可信"),
    ("就要調整判斷", "就要重新看"),
    ("判讀", "解讀"),
    ("時機頁看的是", "現在要判斷的是"),
    ("放到時機上", "以現在的時間點看"),
    ("聯絡狀態上", "以現在的聯絡狀態看"),
    ("測接不接得住", "看對方接不接得住"),
    ("方法邊界", "解讀限制"),
    ("關係重要轉折氣候", "接下來要留意的關係節奏"),
    ("反而讓互動進入防衛", "反而讓氣氛變硬"),
    ("偶爾回覆只代表通道未斷，還不能當成穩定投入", "偶爾回覆只表示還有零星聯絡，不能直接當成關係已經變穩"),
    ("偶爾回覆還不能直接當成穩定投入", "偶爾回覆不能直接當成關係已經變穩"),
    ("偶爾回覆只代表通道未斷，還不能等同穩定投入", "偶爾回覆只表示還有零星聯絡，不能直接當成關係已經變穩"),
    ("副動力要用來分辨值得等待和繼續消耗", "也要分辨這段關係是在變好，還是在繼續消耗你"),
    ("副動力", "旁邊這個提醒"),
    ("單一反應、單一星盤線索或單次訊息替整段關係下結論", "某一次反應或一則訊息替整段關係下結論"),
    ("單一星盤線索", "一個線索"),
    ("把距離直接解讀成不在乎", "一退開就追問他是不是不在乎"),
    ("責任、承諾和距離感會讓回應變得比較保守，就算有在意也可能先退回安全距離", "一談到關係定位或距離，對方可能會先慢下來；這不一定是不在意，而是現在還接不住太重的話題"),
    ("避免推進速度又把對方推進防衛", "避免越想靠近，氣氛越緊"),
    ("穩定投入", "持續行動"),
    ("現實投入", "實際行動"),
    ("通道未斷", "還有零星聯絡"),
    ("通道受阻", "聯絡被擋住"),
    ("自然互動通道", "自然互動"),
    ("自然小通道", "自然小開口"),
    ("沒有自然通道", "沒有能自然開口的位置"),
    ("正常通道", "正常聯絡"),
    ("通道", "聯絡方式"),
    ("行動速度", "靠近的步調"),
    ("直接等於關係答案", "代表關係已經有結果"),
    ("關係答案", "關係結果"),
    ("壓力下的防衛", "緊張時的反應"),
    ("防衛反應", "反應變硬"),
    ("進入防衛", "變得比較緊"),
    ("更防衛", "更緊"),
    ("比較不防衛", "比較不緊"),
    ("防衛", "保護自己"),
)


def humanize_visible_copy(text: Any) -> str:
    value = normalize_zh_text(text)
    for source, target in FINAL_VISIBLE_COPY_REPLACEMENTS:
        value = value.replace(source, target)
    value = re.sub(
        r"把「(?:太陽|月亮|水星|金星|火星|木星|土星|天王星|海王星|冥王星)[-－](?:太陽|月亮|水星|金星|火星|木星|土星|天王星|海王星|冥王星)」當互動火花，不當關係定論",
        "把當下的靠近感當成互動火花，不當關係定論",
        value,
    )
    value = value.replace("。。", "。")
    return normalize_zh_text(value)


def join_zh_clauses(parts: list[Any]) -> str:
    return "；".join(part for part in (zh_clause(item) for item in parts) if part)


def render_zh_summary(template: str, **kwargs: Any) -> str:
    clean_kwargs = {
        key: zh_clause(value) if isinstance(value, str) else value
        for key, value in kwargs.items()
    }
    return normalize_zh_text(template.format(**clean_kwargs))


def unique_strings(values: list[Any] | tuple[Any, ...] | None) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def selector_trace_payload(
    question_selector: dict[str, Any] | None,
    *,
    question_key: str,
    method_claim_ids: list[str] | None = None,
    evidence_cluster_keys: list[str] | None = None,
) -> dict[str, Any]:
    selector = question_selector or {}
    return {
        "version": str(selector.get("version") or "western-question-selector-v1"),
        "questionKey": str(selector.get("questionKey") or question_key),
        "role": str(selector.get("role") or "evidence_weighting_policy"),
        "methodClaimIds": unique_strings([*(selector.get("methodClaimIds") or []), *(method_claim_ids or [])]),
        "evidenceClusterKeys": unique_strings([*(selector.get("evidenceClusterKeys") or []), *(evidence_cluster_keys or [])]),
    }


def zh_order(index: int) -> str:
    return ZH_NUMERALS.get(index, str(index))


def zh_timeline_range(range_label: str) -> str:
    return f"第 {range_label.removeprefix('Day ')} 天" if range_label.startswith("Day ") else range_label


FUNCTION_SIGN_STYLES: dict[str, dict[str, str]] = {
    "Moon": {
        "Aries": "你需要對方反應快一點，有話直接說清楚，心才不會一直懸著。",
        "Taurus": "你會用穩定感確認關係：對方有沒有持續出現、說到做到，對你很重要。",
        "Gemini": "你需要能聊、能問、能把感受講出來；話說開了，心才比較安。",
        "Cancer": "你很在意被記得、被照顧，也需要感覺自己在對方心裡有位置。",
        "Leo": "你需要被重視、被肯定；對方有沒有用心看見你，會直接影響安全感。",
        "Virgo": "你會從日常細節確認一個人是否可靠：事情有沒有處理好、答應的事有沒有做到。",
        "Libra": "你需要關係有來有回，對話公平、彼此都有回應，心才會安定。",
        "Scorpio": "你需要深度信任，不喜歡只停在表面；感受真不真，對你很重要。",
        "Sagittarius": "你需要空間和坦白，也需要感覺這段關係還有往前看的方向。",
        "Capricorn": "你會從責任感和穩定行動裡感覺安全；光說好聽話不太夠。",
        "Aquarius": "你需要被尊重個人空間，也需要像朋友一樣可以理解彼此。",
        "Pisces": "你很容易接收到氣氛和情緒，所以溫柔、同理會讓你比較安心。",
    },
    "Mercury": {
        "Aries": "你說話習慣直接切重點，問題拖太久或講得太模糊，會讓你沒耐心。",
        "Taurus": "你需要具體、穩定、說得到做得到的溝通；空泛承諾會讓你不安心。",
        "Gemini": "你靠對話整理想法，越能問、能聊、能交換資訊，越容易把誤會打開。",
        "Cancer": "你很在意對方說話的口氣；先感覺自己被理解，才比較聽得進道理。",
        "Leo": "你需要被尊重地溝通；如果語氣像否定你，你會很難放鬆對話。",
        "Virgo": "你會想把問題講清楚、拆細節，但語氣要柔一點，才不會像在挑錯。",
        "Libra": "你習慣用協調的方式溝通，希望雙方都有台階，也都有被聽見。",
        "Scorpio": "你需要對話有真誠和深度；只講表面安撫，反而會讓你更不信。",
        "Sagittarius": "你比較能接受坦白和大方向，溝通時需要空間，不喜歡被控制。",
        "Capricorn": "你溝通時會看現實做法和責任感；要修復，就需要看得見的步驟。",
        "Aquarius": "你需要一點理性距離，先想清楚再談，比被情緒推著講更有效。",
        "Pisces": "你很容易受語氣和氣氛影響；溫柔但清楚的話，比逼問更能讓你開口。",
    },
    "Venus": {
        "Aries": "你喜歡直接、有火花的靠近；有感覺時，通常不太想拖太久。",
        "Taurus": "你喜歡慢慢累積的穩定感，陪伴、觸感和生活裡的實際照顧很重要。",
        "Gemini": "你容易被好聊、有趣、有新鮮感的人吸引，互動輕鬆會讓好感升溫。",
        "Cancer": "你會用照顧、記得小事和情緒靠近來表達在意。",
        "Leo": "你喜歡有熱度、被珍惜的感覺，也會用比較明亮的方式表達喜歡。",
        "Virgo": "你常用細節和實際幫忙表達好感，不一定高調，但會做得到。",
        "Libra": "你喜歡一對一的互動，有美感、有禮貌、彼此對等，會讓你更想靠近。",
        "Scorpio": "你喜歡有深度和專注感的靠近，不太滿足於曖昧的表面熱絡。",
        "Sagittarius": "你喜歡自由、坦白、有探索感的關係；太快被綁住會讓熱度下降。",
        "Capricorn": "你喜歡可靠、慢熟、能一起面對現實的人；好感常是慢慢建立的。",
        "Aquarius": "你容易被朋友感、精神連結和保有空間的互動吸引。",
        "Pisces": "你喜歡溫柔、有想像空間、能同理彼此的靠近方式。",
    },
    "Mars": {
        "Aries": "關係要往前走時，你反應很快；生氣時也容易先講先做，之後再調整。",
        "Taurus": "你不會很快往前衝，但一旦認定就很持續；吵架時也比較不容易先讓步。",
        "Gemini": "你會用聊天、反應和機智帶動關係；衝突時也容易越講越多。",
        "Cancer": "你行動時會帶著保護感和情緒記憶，受傷時容易先縮回去。",
        "Leo": "你需要熱度和尊重來推動關係；吵架時，被否定會特別刺痛你。",
        "Virgo": "你會想把問題修好、把細節處理乾淨；衝突時容易卡在哪裡不對。",
        "Libra": "你不喜歡把關係弄僵。想靠近或吵架時，會先找一個雙方都能接受的說法。",
        "Scorpio": "你行動起來很有強度，靠近和衝突都容易碰到信任與控制感。",
        "Sagittarius": "你需要方向和自由感才會想往前；一被限制，反應會很快變強。",
        "Capricorn": "你面對關係進展會比較謹慎，會先看目標、責任和長期可不可行。",
        "Aquarius": "你行動時需要保有自主和理性距離；衝突太情緒化時會想拉開。",
        "Pisces": "你常憑感覺和共鳴行動；衝突太硬時，會想先避開正面碰撞。",
    },
    "Saturn": {
        "Aries": "壓力一大，你會卡在要不要主動出手；怕衝太快，也怕被拒絕後失控。",
        "Taurus": "你最怕穩定感被動搖，所以壓力來時會先守住原狀，改變會變慢。",
        "Gemini": "壓力會卡在怎麼說清楚；越不知道怎麼講，越容易延遲回覆。",
        "Cancer": "壓力一靠近情緒安全，你會先保護自己，不太容易立刻打開。",
        "Leo": "壓力會碰到自尊和被看見的需求，受傷時容易變硬或沉默。",
        "Virgo": "壓力來時，你容易先找問題、整理細節，用控制感代替脆弱。",
        "Libra": "壓力會落在關係是否對等；你怕破壞平衡，所以容易拖著不表態。",
        "Scorpio": "壓力會碰到信任和失控感，你可能先關起來，觀察對方值不值得相信。",
        "Sagittarius": "壓力一像限制，你會先想退到有空間的地方。",
        "Capricorn": "壓力會讓你更慎重、更現實，承諾和放鬆都會變慢。",
        "Aquarius": "壓力太情緒化時，你會退到理性距離裡，先保住自己的自主感。",
        "Pisces": "壓力太模糊或太滿時，你容易消失一下，先讓自己不要被情緒淹沒。",
    },
}


FUNCTION_SIGN_TENSIONS: dict[str, dict[str, str]] = {
    "Moon": {
        "Aries": "等不到明確回應時，容易把不安變成急著追問。",
        "Taurus": "節奏被打亂時，容易先固守原狀，不想太快重新相信。",
        "Gemini": "資訊不清楚時，容易想太多，用反覆確認處理不安。",
        "Cancer": "感覺不被接住時，容易退回自己的殼裡。",
        "Leo": "沒有被重視時，容易把受傷藏在自尊後面。",
        "Virgo": "情緒混亂時，容易先找問題和細節，反而更難放鬆。",
        "Libra": "關係不平衡時，容易一直觀察對方反應，忘了說自己的需要。",
        "Scorpio": "信任感不足時，容易把感受收深，先測試再靠近。",
        "Sagittarius": "被限制時，容易用拉開距離保護自己的安全感。",
        "Capricorn": "壓力大時，容易先變得懂事和克制，不讓脆弱露出來。",
        "Aquarius": "情緒太近時，容易退到理性距離裡。",
        "Pisces": "氛圍太混亂時，容易吸收太多情緒，分不清自己的感受。",
    },
    "Mercury": {
        "Aries": "話還沒說完就想推進，容易讓對方感覺被催促。",
        "Taurus": "沒有具體證據時，容易不想改口，對話變慢。",
        "Gemini": "資訊太多時，容易跳題，核心感受反而沒有被說清。",
        "Cancer": "語氣不安全時，容易先聽見情緒，聽不進內容。",
        "Leo": "被否定時，會比較想保護面子，對話容易變硬。",
        "Virgo": "想把問題講精準時，容易讓對方聽成挑剔。",
        "Libra": "太想保持和氣時，容易把真正的立場說得不夠清楚。",
        "Scorpio": "感覺對方不真誠時，容易追深，讓對話變得有壓力。",
        "Sagittarius": "想講大方向時，容易略過對方此刻需要的細節。",
        "Capricorn": "太重視結果和責任時，語氣容易變得嚴肅。",
        "Aquarius": "太理性時，容易讓對方覺得感受被放在一邊。",
        "Pisces": "太怕傷人時，容易說得含糊，讓修復拖更久。",
    },
    "Venus": {
        "Aries": "熱度來得快時，也容易對慢回應失去耐心。",
        "Taurus": "需要穩定累積時，容易不喜歡太突然的關係變化。",
        "Gemini": "好感靠互動流動時，容易害怕關係變得太沉重。",
        "Cancer": "在意變深時，容易把照顧和安全感綁在一起。",
        "Leo": "需要被看見時，容易對冷淡或敷衍特別敏感。",
        "Virgo": "用細節表達在意時，容易默默付出又希望對方懂。",
        "Libra": "重視互惠時，容易在不平衡裡忍太久。",
        "Scorpio": "好感變深時，容易想確認專注和唯一性。",
        "Sagittarius": "需要自由感時，容易對太快定義關係有壓力。",
        "Capricorn": "慢熟謹慎時，容易把喜歡藏在責任和實際行動裡。",
        "Aquarius": "需要朋友感和空間時，容易讓親密看起來比較淡。",
        "Pisces": "容易理想化靠近，也容易被氛圍牽動。",
    },
    "Mars": {
        "Aries": "一被觸發就想立刻行動，容易先衝再後悔。",
        "Taurus": "一旦立場固定，容易僵持，不想先退。",
        "Gemini": "衝突時容易用話語反應，越講越分散。",
        "Cancer": "受威脅時會先保護自己，行動容易帶情緒記憶。",
        "Leo": "被否定時，容易把衝突升高成尊嚴問題。",
        "Virgo": "想修正問題時，容易卡在細節和對錯。",
        "Libra": "想協調又有怒氣時，容易在忍讓和爆發之間搖擺。",
        "Scorpio": "被觸動深層信任時，衝突容易變得很強烈。",
        "Sagittarius": "被限制時，容易想立刻逃離或反抗。",
        "Capricorn": "壓力下會想控制局面，行動變得硬。",
        "Aquarius": "衝突太情緒化時，容易抽離或突然拉開距離。",
        "Pisces": "不想硬碰硬時，容易迴避直接表態。",
    },
    "Saturn": {
        "Aries": "害怕衝動失控時，會延遲出手或突然變硬。",
        "Taurus": "安全感被動搖時，會放慢改變，先守住原狀。",
        "Gemini": "不知道怎麼說清楚時，容易延遲回覆或切斷話題。",
        "Cancer": "情緒安全被威脅時，會退回保護殼裡。",
        "Leo": "自尊受傷時，會變得沉默或不願示弱。",
        "Virgo": "壓力來時，會用挑剔和整理代替表達害怕。",
        "Libra": "怕破壞平衡時，會拖延表態。",
        "Scorpio": "信任風險變高時，會關閉、保留或測試。",
        "Sagittarius": "自由被壓縮時，會先拉開距離。",
        "Capricorn": "責任壓力變重時，會更慢、更慎重，也更不容易放鬆。",
        "Aquarius": "怕被情緒吞沒時，會理性化並拉開距離。",
        "Pisces": "界線模糊時，會消散、逃避或沉默。",
    },
}


FUNCTION_MEANINGS = {
    "Moon": "月亮這張卡看的是一個人在不安、脆弱或需要被安撫時，什麼反應會讓心比較穩",
    "Mercury": "水星這張卡看的是一個人怎麼理解訊息、怎麼開口，以及誤會後怎麼把話說回來",
    "Venus": "金星這張卡看的是一個人怎麼表達喜歡、怎麼感覺被吸引，也怎麼感覺自己被放在心上",
    "Mars": "火星這張卡看的是一個人怎麼主動、怎麼推進關係，以及衝突或生氣時會怎麼出手",
    "Saturn": "土星這張卡看的是一個人在壓力下怕什麼、怎麼設界線，以及為什麼會變慢或退開",
}


FUNCTION_SIGN_SUBJECTS = {
    "Moon": "安全感需求",
    "Mercury": "溝通方式",
    "Venus": "喜歡與被重視的方式",
    "Mars": "行動和衝突反應",
    "Saturn": "壓力與防衛模式",
}


SIGN_DEFINITIONS = {
    "Aries": "直接、快速、開創，需要反應清楚",
    "Taurus": "穩定、感官、持續，重視安全與節奏",
    "Gemini": "好奇、交流、多角度，需要資訊流動",
    "Cancer": "情感記憶、照顧、防護，需要歸屬感",
    "Leo": "表達、自尊、熱度，需要被真實看見",
    "Virgo": "分析、整理、改善，重視細節與實際幫助",
    "Libra": "協調、互惠、審美，會先尋找平衡",
    "Scorpio": "深度、界線、信任，感受強烈但不輕易外露",
    "Sagittarius": "自由、探索、誠實，需要空間與方向",
    "Capricorn": "責任、結構、長期，重視現實承擔",
    "Aquarius": "獨立、觀察、理念，需要心理空間",
    "Pisces": "敏感、共感、想像，容易接收環境情緒",
}


POINT_DOMAINS = {
    "Moon": "安全感",
    "Mercury": "溝通",
    "Venus": "好感",
    "Mars": "行動與衝突",
    "Saturn": "界線與壓力",
}


ELEMENT_TEXTURES = {
    "Fire": "直接和速度",
    "Earth": "穩定和實際",
    "Air": "討論與心理空間",
    "Water": "感受和安全感",
}


FUNCTION_ELEMENT_REACTIONS: dict[str, dict[str, str]] = {
    "Moon": {
        "Fire": "{subject}需要明確、快速的回應，情緒才不會一直懸著",
        "Earth": "{subject}靠穩定出現、說到做到和生活細節建立安全感",
        "Air": "{subject}需要把話說開，也需要一點空間整理情緒",
        "Water": "{subject}需要感覺被接住、被在乎，情緒才比較能放鬆",
    },
    "Mercury": {
        "Fire": "{subject}溝通時喜歡直接講重點，問題拖太久會容易急",
        "Earth": "{subject}需要具體、穩定、說了能落地的溝通",
        "Air": "{subject}靠討論、釐清和交換想法來修復誤會",
        "Water": "{subject}很在意對方說話的口氣；先感覺自己被理解，才比較談得下去",
    },
    "Venus": {
        "Fire": "{subject}喜歡直接、有火花的靠近，好感來時不太想拖太久",
        "Earth": "{subject}喜歡慢慢累積的穩定和實際照顧",
        "Air": "{subject}容易被好聊、輕鬆、有空間的互動吸引",
        "Water": "{subject}喜歡溫柔、被記得和情緒上的靠近",
    },
    "Mars": {
        "Fire": "{subject}推進或生氣時反應快，傾向先把方向講出來",
        "Earth": "{subject}推進比較慢但持續，衝突時也不容易立刻轉彎",
        "Air": "{subject}會用對話、協調或拉開距離來處理行動和衝突",
        "Water": "{subject}的行動會受情緒安全影響，受傷時容易先退回去",
    },
    "Saturn": {
        "Fire": "{subject}面對壓力時會卡在要不要主動，怕太快也怕被拒絕",
        "Earth": "{subject}面對壓力時會先守住穩定，改變需要慢慢來",
        "Air": "{subject}遇到壓力時，會先拉出一點距離，用理性、討論或觀察讓自己穩住",
        "Water": "{subject}遇到壓力時會先保護感受，需要安全後才比較敢打開",
    },
}


FIT_ITEM_MEANINGS = {
    "Moon": "兩個人建立安全感和接受安撫的方式，可以放在一起比較。",
    "Mercury": "兩個人溝通和把誤會說回來的方式，可以放在一起比較。",
    "Venus": "兩個人靠近、表達喜歡和感受吸引的方式，可以放在一起比較。",
    "Mars": "兩個人推進關係和處理衝突的方式，可以放在一起比較。",
    "Saturn": "兩個人遇到壓力、界線和關係變慢時的反應，可以放在一起比較。",
}


FIT_ITEM_RELATION_ENDINGS = {
    "natural": {
        "Moon": "所以情緒起來時，彼此比較知道怎麼讓對方安心。",
        "Mercury": "所以有誤會時，彼此比較容易用聽得懂的方式把話說回來。",
        "Venus": "所以靠近時，彼此比較容易感覺到好感和善意。",
        "Mars": "所以要推進或吵起來時，彼此比較快知道對方的節奏在哪裡。",
        "Saturn": "所以遇到壓力或界線時，彼此比較容易看懂對方是在保護自己，不一定是在拒絕。",
    },
    "effort": {
        "Moon": "如果沒有先說清楚，一方可能以為自己在安撫，另一方卻覺得沒有被接住。",
        "Mercury": "如果沒有先說清楚，一方可能以為自己講得很清楚，另一方卻只聽見壓力。",
        "Venus": "如果沒有先說清楚，一方以為在表達好感，另一方可能感覺不到，或覺得太滿。",
        "Mars": "如果沒有先說清楚，一方覺得在解決問題，另一方可能覺得被催促或被推著走。",
        "Saturn": "如果沒有先說清楚，一方其實是在保護自己，另一方可能會看成冷淡或退縮。",
    },
    "friction": {
        "Moon": "情緒敏感時，很容易一邊急著要回應，一邊只想先安靜。",
        "Mercury": "越急著講清楚，越可能把對方逼到防衛裡。",
        "Venus": "靠近的速度和表達方式不同，容易讓一方覺得太冷，另一方覺得太逼。",
        "Mars": "衝突時很容易一邊想立刻處理，一邊覺得被壓迫。",
        "Saturn": "壓力上來時，一方越想確認，另一方越可能先退開。",
    },
}


def function_element_reaction(point: str, element: str, fallback_label: str, subject: str) -> str:
    template = (FUNCTION_ELEMENT_REACTIONS.get(point) or {}).get(element)
    if template:
        return template.format(subject=subject)
    texture = ELEMENT_TEXTURES.get(element, fallback_label)
    if subject == "你":
        return f"你在這一項比較偏向{texture}的反應"
    return f"對方在這一項比較偏向{texture}的反應"


def role_adjusted_relationship_text(text: Any, role_label: str) -> str:
    value = normalize_zh_text(text)
    if role_label == "你":
        return value
    target_swaps = [
        ("你需要對方", "__SUBJECT_NEEDS_YOU__"),
        ("對方有沒有", "__YOU_HAVE_OR_NOT__"),
        ("讓對方", "__MAKES_YOU__"),
        ("對方覺得", "__YOU_FEEL__"),
        ("對方聽成", "__YOU_HEAR_AS__"),
        ("對方此刻", "__YOU_RIGHT_NOW__"),
        ("對方懂", "__YOU_UNDERSTAND__"),
        ("對方不真誠", "__YOU_NOT_SINCERE__"),
    ]
    for old, placeholder in target_swaps:
        value = value.replace(old, placeholder)
    replacements = [
        ("對你很重要", "這點對對方很重要"),
        ("讓你", "讓對方"),
        ("你的", "對方的"),
        ("你會", "對方會"),
        ("你需要", "對方需要"),
        ("你習慣", "對方習慣"),
        ("你很", "對方很"),
        ("你比較", "對方比較"),
        ("你常", "對方常"),
        ("你容易", "對方容易"),
        ("你喜歡", "對方喜歡"),
        ("你最怕", "對方最怕"),
        ("你行動", "對方行動"),
        ("你反應", "對方反應"),
        ("你推進", "對方推進"),
        ("你不會", "對方不會"),
        ("你不喜歡", "對方不喜歡"),
        ("你不太", "對方不太"),
        ("你可能", "對方可能"),
    ]
    for old, new in replacements:
        value = value.replace(old, new)
    target_outputs = {
        "__SUBJECT_NEEDS_YOU__": "對方需要你",
        "__YOU_HAVE_OR_NOT__": "你有沒有",
        "__MAKES_YOU__": "讓你",
        "__YOU_FEEL__": "你覺得",
        "__YOU_HEAR_AS__": "你聽成",
        "__YOU_RIGHT_NOW__": "你此刻",
        "__YOU_UNDERSTAND__": "你懂",
        "__YOU_NOT_SINCERE__": "你不真誠",
    }
    for placeholder, output in target_outputs.items():
        value = value.replace(placeholder, output)
    return normalize_zh_text(value)


def person_function_sign_readable_interpretation(
    *,
    point: str,
    sign: str,
    sign_label: str,
    role_label: str,
    placement: str,
    fallback_body: str,
    fallback_stuck_pattern: str,
    confidence: str,
    source_claim_ids: list[str] | None = None,
) -> ReadableInterpretation:
    raw_body = (FUNCTION_SIGN_STYLES.get(point) or {}).get(sign, fallback_body)
    raw_stuck = (FUNCTION_SIGN_TENSIONS.get(point) or {}).get(sign, fallback_stuck_pattern)
    sign_definition = SIGN_DEFINITIONS.get(sign, "需要放回完整星盤判斷")
    function_meaning = FUNCTION_MEANINGS.get(point, "這個點位需要放回完整星盤判斷")
    function_subject = FUNCTION_SIGN_SUBJECTS.get(point, "這個反應")
    if sign_label:
        meaning = f"{function_meaning}。落在{sign_label}時，{function_subject}會帶著「{sign_definition}」的風格。"
    else:
        meaning = function_meaning
    confidence_note = "出生時間未知，月亮相關語氣會保守處理。" if point == "Moon" and confidence == "low" else None
    body = role_adjusted_relationship_text(raw_body, role_label)
    stuck = role_adjusted_relationship_text(raw_stuck, role_label)
    if role_label == "對方":
        body = body.replace("對方", "他")
        stuck = stuck.replace("對方", "他")
    return {
        "version": "readable-interpretation-v1",
        "module": "person_function_sign",
        "locale": "zh-TW",
        "headline": placement,
        "meaning": normalize_zh_text(meaning),
        "body": normalize_zh_text(body),
        "stuckPattern": normalize_zh_text(stuck),
        "confidenceNote": confidence_note,
        "sourceClaimIds": source_claim_ids or [],
        "debug": {
            "point": point,
            "sign": sign,
            "roleLabel": role_label,
        },
    }


def fit_item_readable_interpretation(
    *,
    point: str,
    relation: str,
    relation_label: str,
    title: str,
    person_a_element: str,
    person_a_element_label: str,
    person_b_element: str,
    person_b_element_label: str,
    confidence: str,
    source_claim_ids: list[str] | None = None,
) -> ReadableInterpretation:
    domain = POINT_DOMAINS.get(point, "互動")
    a_reaction = function_element_reaction(point, person_a_element, person_a_element_label, "你")
    b_reaction = function_element_reaction(point, person_b_element, person_b_element_label, "對方")
    if relation == "natural":
        ending = (FIT_ITEM_RELATION_ENDINGS["natural"]).get(point, f"所以在{domain}上，彼此比較容易知道對方需要什麼。")
        body = f"{a_reaction}；{b_reaction}。{ending}"
        next_move = "先從這個比較順的地方互動，讓對方比較容易接住，把它維持在日常小互動裡。"
    elif relation == "effort":
        ending = (FIT_ITEM_RELATION_ENDINGS["effort"]).get(point, "兩邊的表達方式不同，同一件事容易被說成兩種語言。")
        body = f"{a_reaction}；{b_reaction}。{ending}"
        next_move = "先把各自需要說成具體做法，少用猜測對方心意的方式互動。"
    else:
        ending = (FIT_ITEM_RELATION_ENDINGS["friction"]).get(point, "靠近或有壓力時，一方的反應可能會被另一方解讀成不在乎、太急或太防衛。")
        body = f"{a_reaction}；{b_reaction}。{ending}"
        next_move = "先把反應收小，問清楚對方現在能承受什麼，把退開或急躁先當成承受度訊號。"
    return {
        "version": "readable-interpretation-v1",
        "module": "fit_summary_item",
        "locale": "zh-TW",
        "headline": f"{title}：{relation_label}",
        "meaning": FIT_ITEM_MEANINGS.get(point, f"這一項比較的是兩個人在{domain}上的基本反應方式。"),
        "body": normalize_zh_text(body),
        "nextMove": normalize_zh_text(next_move),
        "confidenceNote": "其中一方資料精度較低，這一項只能保守參考。" if confidence == "low" else None,
        "sourceClaimIds": source_claim_ids or [],
        "debug": {
            "point": point,
            "relation": relation,
            "personAElement": person_a_element,
            "personBElement": person_b_element,
        },
    }


def fit_summary_readable_interpretation(
    *,
    natural_count: int,
    effort_count: int,
    friction_count: int,
    source_claim_ids: list[str] | None = None,
) -> ReadableInterpretation:
    if friction_count and friction_count >= natural_count:
        headline = "先看容易摩擦的地方，再談答案"
        body = "你們有吸引和理解的線索，也有一些反應方式容易撞在一起。先把最容易摩擦的地方降溫，後面的問題才比較能被真正討論。"
    elif natural_count:
        headline = "有自然接得上的地方，但還要看壓力"
        body = "你們有幾個地方反應比較容易接上，這會讓關係有熟悉感；但能不能走穩，還要看壓力和修復方式有沒有跟上。"
    else:
        headline = "這段關係需要更多對齊"
        body = "目前比較明顯的是反應節奏不同。先把彼此的需要說成具體、做得到的互動方式，關係才比較有空間重新對齊。"
    return {
        "version": "readable-interpretation-v1",
        "module": "fit_summary",
        "locale": "zh-TW",
        "headline": headline,
        "meaning": "兩個人的本命關係功能怎麼接上或互相誤會，會指出最需要處理的互動位置。",
        "body": normalize_zh_text(body),
        "sourceClaimIds": source_claim_ids or [],
        "debug": {
            "naturalCount": natural_count,
            "effortCount": effort_count,
            "frictionCount": friction_count,
        },
    }


QUESTION_FOCUS_MEANINGS = {
    "still-love-me": "這一段回答的是：還看不看得到在意與反應，以及回應能不能穩定延續。",
    "any-chance": "這一段回答的是：機會要靠哪些條件打開，舊模式要先在哪裡停下來。",
    "when-to-contact": "這一段回答的是：現在適不適合開口，以及什麼語氣比較不會讓互動更緊。",
    "what-did-i-do-wrong": "這一段回答的是：互動怎麼卡住，哪個循環可以先調整。",
    "stay-or-let-go": "這一段先分清楚：你還在意，同時也要看自己會不會越等越累。",
}


QUESTION_ANSWER_HEADLINES = {
    "still-love-me": "有反應，先看能不能穩定延續",
    "any-chance": "有條件，先把追問強度降下來",
    "when-to-contact": "先看狀態，再決定要不要開口",
    "what-did-i-do-wrong": "把責任放回互動循環裡看",
    "stay-or-let-go": "先看這段互動會不會讓你更累",
}


QUESTION_ANSWER_CAUTIONS = {
    "still-love-me": "重點放在反應、緊繃感與可觀察行動。",
    "any-chance": "機會線索要回到互動能不能真的變穩。",
    "when-to-contact": "時機用來決定靠近方式和訊息大小。",
    "what-did-i-do-wrong": "星盤幫你看見互動循環和可以調整的位置。",
    "stay-or-let-go": "不要只因為還有感覺就繼續撐，也不要在情緒最高點做最後決定。",
}


QUESTION_PRIMARY_ANSWER_FRAMES = {
    "still-love-me": "先看穩定回應與可延續互動：",
    "any-chance": "先看修復條件和互動承受度：",
    "when-to-contact": "先看現在適不適合開口，訊息必須短、輕、沒有要求：",
    "what-did-i-do-wrong": "先看可調整的互動循環：",
    "stay-or-let-go": "先看這段互動會不會讓你更累：",
}


QUESTION_EVIDENCE_HIGHLIGHT_TITLES = {
    "still-love-me": {
        "theme": "反覆出現的反應線索",
        "contact": "穩定回應的現實狀態",
        "timing": "回應能否變穩",
        "evidence": ["穩定回應線索", "表態門檻線索", "需要回到現實確認的事"],
    },
    "any-chance": {
        "theme": "反覆出現的修復條件",
        "contact": "修復條件的現實狀態",
        "timing": "修復時機",
        "evidence": ["修復條件線索", "舊模式門檻", "重啟可能線索"],
    },
    "when-to-contact": {
        "theme": "反覆出現的開口前線索",
        "contact": "開口前的現實狀態",
        "timing": "開口時機",
        "evidence": ["開口前先看什麼", "對方接不接得住", "需要避開的時候"],
    },
    "what-did-i-do-wrong": {
        "theme": "反覆出現的互動循環",
        "contact": "自責拆解的現實狀態",
        "timing": "情緒降溫狀態",
        "evidence": ["可調整的互動", "互相觸發線索", "不該全責化的事"],
    },
    "stay-or-let-go": {
        "theme": "反覆出現的等待條件",
        "contact": "等待條件的現實狀態",
        "timing": "觀察與界線",
        "evidence": ["等待條件線索", "需要先停下來的訊號", "需要看見的行動"],
    },
}


NORMAL_USER_BLOCK_LABELS = {
    "directAnswer": "先說結論",
    "whyThisMatters": "為什麼這樣看",
    "whatToWatch": "接下來看什麼",
    "nextStep": "現在怎麼做",
    "stopLine": "先不要做什麼",
}


NORMAL_USER_HEADLINES = {
    "still-love-me": "有反應，先看能不能穩定延續",
    "any-chance": "機會要看條件和互動承受度",
    "when-to-contact": "先看能不能輕一點開口",
    "what-did-i-do-wrong": "先把問題放回互動循環裡看",
    "stay-or-let-go": "先看等待會不會讓你更累",
}


NORMAL_USER_DIRECT_ANSWERS = {
    "still-love-me": {
        "default": "先看他有沒有可觀察的反應，以及這些反應能不能穩定延續。",
        "blocked": "聯絡方式已經關上時，先尊重邊界，把重點放回現實回應。",
        "no-contact": "目前先看還有沒有反應線索，以及沉默之後是否出現自然互動。",
        "live": "你們還有互動時，重點是看回應有沒有變穩、變自然、變可延續。",
    },
    "any-chance": {
        "default": "機會要看舊模式能不能停下來，以及互動是否能重新變輕、變穩。",
        "blocked": "現在不適合把機會寫成主動追回；對方已經關上通道時，先守住界線。",
        "no-contact": "還有機會也先放在觀察裡；一次訊息只適合輕輕試水溫。",
        "live": "你們還有互動空間；是否重新靠近，要看對話有沒有變輕、變穩。",
    },
    "when-to-contact": {
        "default": "現在適不適合用很輕的方式開口，以及訊息要放到多小，要由互動承受度決定。",
        "blocked": "現在先不要主動聯絡。被封鎖或通道關上時，好時機也要讓位給界線。",
        "no-contact": "如果真的要開口，也只能是一句短、輕、沒有要求的訊息，送出後先停。",
        "live": "你們還能說話時，不需要另外找一天把關係題攤開；先把原本對話放輕。",
    },
    "what-did-i-do-wrong": {
        "default": "先看哪個互動循環可以調整，把問題拆回具體對話和反應。",
        "blocked": "即使你有想修正的地方，也要先尊重對方已經畫出的邊界。",
        "no-contact": "現在先不要用自責逼自己補救；先看哪一種靠近方式會讓關係更緊。",
        "live": "你們還能互動時，重點是改一個看得見的表達方式，把話說清楚一點就先停。",
    },
    "stay-or-let-go": {
        "default": "現在要把等待放小一點。你可以還在意他，但主要策略要回到觀察與界線。",
        "blocked": "現在比較需要先停下來保護自己，不適合用等待或繞路聯絡換答案。",
        "no-contact": "現在不適合只靠等待；沒有自然對話通道時，要先看對方會不會自己打開一點空間。",
        "live": "還不到一定要放下，但也不適合無限期等下去；先看互動會不會變穩。",
    },
}


NORMAL_USER_THEME_REASONS = {
    "saturn_pressure": "這段關係一靠近就容易變沉重，對方可能先用慢、冷或防衛保護自己。",
    "emotional_safety": "你們的核心在於脆弱和不安出現時，彼此能不能接得住。",
    "communication_repair": "你們卡住的地方常在說法。一句話如果像追問、說服或逼表態，對方就容易退開。",
    "attraction_pursuit": "吸引和火花可以看見，但火花如果沒有穩定回應，很容易變成一下靠近、一下退開。",
    "action_conflict": "你們一靠近時，速度容易變急，對話也容易從想處理變成衝突。",
    "identity_rhythm": "這段互動容易碰到自尊和被尊重的感覺；越逼對方承認，越容易讓他先保護自己。",
    "outer_intensity": "強烈感受是真實線索，還要回到可觀察的行動。",
}


NORMAL_USER_THEME_WATCH = {
    "saturn_pressure": "靠近時氣氛有沒有變比較不沉重，對方是否不用被逼也願意回應。",
    "emotional_safety": "你說出感受時，對方是否比較接得住，退開或變冷有沒有減少。",
    "communication_repair": "訊息變短、變清楚後，對話有沒有比較容易回來。",
    "attraction_pursuit": "有火花之後，對方有沒有穩定延續，熱一下又退開的狀態有沒有減少。",
    "action_conflict": "你一靠近時，對話會不會又變急、變緊，甚至變成衝突。",
    "identity_rhythm": "對話有沒有保留彼此台階，讓對方比較不需要防衛。",
    "outer_intensity": "強烈感受之外，對方有沒有清楚、持續、可看見的行動。",
}


NORMAL_USER_QUESTION_WATCH = {
    "still-love-me": [
        "他有沒有持續回應，偶爾丟一點反應之外是否還有延續。",
        "回應裡有沒有自然延伸，你追著要答案的次數有沒有變少。",
    ],
    "any-chance": [
        "舊的卡住模式有沒有真的停下來。",
        "互動能不能變輕、變穩，熱絡之後是否還能延續。",
    ],
    "when-to-contact": [
        "你現在開口，是想輕輕靠近，還是想立刻要答案。",
        "訊息能不能短、輕、沒有要求，送出後也能停下來。",
    ],
    "what-did-i-do-wrong": [
        "哪一段互動可以調整，讓你不用把全部責任扛回自己身上。",
        "你的道歉或解釋會讓對話變清楚，還是讓壓力更重。",
    ],
    "stay-or-let-go": [
        "他是不是有持續、自然、穩定的回應。",
        "你等下去之後，是比較安心，還是越來越累。",
    ],
}


NORMAL_USER_NEXT_STEPS = {
    "blocked": "先不要換帳號、請人傳話或用其他方式繞過去；現在最重要的是守住界線。",
    "no-contact": "先看自然回應，不追回答案。如果真的要說一句，只能短、輕、能自然停下。",
    "occasional-contact": "跟著對方的回應走。回得少，就說少一點；有自然延續，再慢慢接下去。",
    "still-in-contact": "用原本通道，把語氣放輕。先只處理一件具體小事，讓對話有台階可以停。",
    "living-or-working-together": "把共同場域先保護好。維持自然、普通、能停下，不把場合變成關係審問。",
}

NORMAL_USER_QUESTION_NEXT_STEPS = {
    ("still-love-me", "no-contact"): "接下來看兩個線索：他有沒有自然延續，以及回應後能不能回到日常互動；若完全沒有自然訊號，就不要用一則訊息逼出答案。",
    ("any-chance", "no-contact"): "先分清楚是情緒回頭，還是行動真的回來：有沒有固定回應、安排，或願意把話題接下去。",
    ("what-did-i-do-wrong", "no-contact"): "把焦點從自責改成互動迴圈：哪一類話題讓他關上，哪一種說法讓對話還能留下。",
    ("stay-or-let-go", "no-contact"): "看這段關係是讓你更清楚，還是更消耗；如果只有牽動沒有投入，把注意力放回自己的安定。",
}


NORMAL_USER_STOP_LINES = {
    "blocked": "不要把星盤或時機當成突破邊界的理由。",
    "no-contact": "如果他沒有自然延續，就先停下來，不要再補第二段。",
    "occasional-contact": "不要把一次回覆放大成承諾，也不要立刻推到復合或關係定位。",
    "still-in-contact": "不要因為還能聊天，就立刻要求對方給關係答案。",
    "living-or-working-together": "不要在共同場域逼談關係，也不要讓對方被迫表態。",
}


NORMAL_USER_RISK_MODIFIERS = {
    "anxious": "如果你現在很想確認，先把動作放小；越急越容易讓對方感覺被追著回答。",
    "self-blaming": "如果你正在自責，先把「我的錯」改成「哪個互動可以調整」。",
    "desperate": "如果你現在很痛、很想立刻有答案，先不要用訊息做最後決定。",
    "unsafe-or-overwhelmed": "如果情緒已經撐不住，先把自己放回安全位置，再談關係下一步。",
}


PUBLIC_ANSWER_REPLACEMENTS = {
    "免費頁": "這份解讀",
    "免費版": "這份解讀",
    "免費結果": "這份解讀",
    "付費報告": "後續章節",
    "完整報告": "後續章節",
    "精準日期": "指定日期",
    "精準日": "指定日期",
    "不排指定日期": "不指定哪一天",
    "不排精準聯絡日": "不指定哪一天聯絡",
    "低刺激": "短、輕、能自然停下",
    "低壓": "壓力較輕",
    "低壓靠近入口": "壓力較輕的靠近方式",
    "可不回": "對方可以先不回",
    "不保證對方會回來": "不能當成對方會回來的證明",
    "保證對方會回來": "當成對方會回來的證明",
    "不保證會回來": "不能當成會回來的證明",
    "保證會回來": "當成會回來的證明",
    "窗口": "時段",
    "靠近的入口": "靠近方式",
    "修復入口": "可以修復的地方",
    "協調入口": "可以協調的地方",
    "完整星盤證據鏈": "完整星盤依據",
    "證據鏈": "星盤依據",
    "壓力訊號": "緊繃感",
    "互動機制": "相處方式",
    "節奏校準": "步調調整",
    "關係容器": "相處空間",
    "行動邊界": "行動尺度",
    "需要慢一點": "需要把動作放小",
    "沒有有反應": "沒有反應",
    "Moon/Venus": "月亮與金星",
    "月亮/金星": "月亮與金星",
    "月亮與金星在乎和需要被照顧的方式": "月亮與金星代表的安全感和被重視感",
    "需求語言": "在乎和需要被照顧的方式",
    "安全感語言": "需要安全感的方式",
    "被重視語言": "需要被重視的方式",
    "安全感與被重視的橋接": "安全感和被重視的感覺怎麼接上",
    "安全感與被重視的接得上的地方": "安全感和被重視的感覺怎麼接上",
    "把安全感和被重視的感覺怎麼接上說清楚": "說清楚你們在哪些地方能讓彼此安心、覺得被重視",
    "交叉橋接": "能互相接上的地方",
    "橋接": "接得上的地方",
    "有橋": "有能接上的地方",
    "讓這個橋變得可用": "讓這個連結真的用得上",
    "控速、降刺激": "先把動作收小、不要再加壓",
    "降速、降刺激": "把步調收小、不要再加壓",
    "降低刺激": "降低壓力",
    "降刺激": "不要再加壓",
    "控速": "把步調收小",
    "推進速度與衝突反應重複出現": "一靠近就容易變急或起衝突",
    "推進速度和衝突反應": "靠近時變急或起衝突的反應",
    "推進速度與衝突反應": "靠近時變急或起衝突的反應",
    "責任與長期承接入口": "能不能穩定負責的地方",
    "責任與長期承接位置": "能不能穩定負責的地方",
    "長期承接位置": "穩定負責的地方",
    "壓力層承接": "壓力能不能被處理",
    "現實回應承接": "穩定的現實回應",
    "情緒承接位置": "情緒比較容易被接住的位置",
    "情緒承接": "情緒比較容易被接住",
    "可預期承接": "可預期回應",
    "成熟承接": "成熟回應",
    "被安全承接": "被安全地接住",
    "被承接": "被接住",
    "可承接": "比較接得住",
    "是否能承接": "能不能接住",
    "能否承接": "能不能接住",
    "能承接": "能接住",
    "穩定承接": "穩定接住",
    "需要翻譯": "需要說清楚",
    "先翻譯成": "先說成",
    "修復槓桿": "可以怎麼修",
    "行動尺度": "接下來適合做到哪一步",
    "開口門檻": "開口前先看什麼",
    "精準證據": "主要依據",
    "orb 約": "角度差約",
    "先降壓": "先讓壓力降下來",
    "降壓": "讓壓力降下來",
    "星盤只能支持很小的試水溫": "目前只適合很小、很輕地試一次",
    "短、輕、可退場": "短、輕、能自然停下",
    "壓力比較小": "壓力較輕",
    "先放慢": "先把步調收小",
    "速度要先放慢": "動作要先收小",
    "把速度放慢": "把動作收小",
    "速度放慢": "動作收小",
    "放慢": "收小",
    "不要急著": "先不用",
    "不急著": "先不",
    "先先不用": "先不用",
    "先先不": "先不",
    "先觀察": "先看",
    "攤牌": "把關係題一次攤開",
    "另一條線索": "旁邊這個提醒",
    "這裡應": "要",
    "Moon": "月亮",
    "Venus": "金星",
    "Mercury": "水星",
    "Mars": "火星",
    "Saturn": "土星",
    "synastry": "合盤",
    "聯絡 timing 行動 reducer": "聯絡時機判斷",
    "timing 行動 reducer": "聯絡時機判斷",
    "contact timing action reducer": "聯絡時機判斷",
    "聯絡 聯絡時機": "聯絡時機",
    "timing selector": "時機篩選",
    "timing": "時機",
    "reducer": "判斷",
    "selector": "篩選",
    "planets": "行星",
    "angles": "軸線",
    "aspects": "相位",
    "houses": "宮位",
    "signs": "星座",
    "Hand 符號系統": "占星符號系統",
    "soft_tone": "先用柔和、不逼答案的語氣",
    "hard_boundary": "明確界線",
    "boundary_only": "只守界線",
}


def sanitize_public_answer_text(text: Any) -> str:
    value = str(text or "").strip()
    for old, new in PUBLIC_ANSWER_REPLACEMENTS.items():
        value = value.replace(old, new)
    return normalize_zh_text(value)


def repeated_theme_context_value(relationship_theme: dict[str, Any] | None, key: str) -> str:
    if not isinstance(relationship_theme, dict):
        return ""
    return sanitize_public_answer_text(relationship_theme.get(key))


def repeated_theme_compact_metadata(relationship_theme: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(relationship_theme, dict) or not relationship_theme.get("themeKey"):
        return {}
    return {
        "themeKey": relationship_theme.get("themeKey"),
        "relationshipThemeLabel": relationship_theme.get("label"),
        "source": relationship_theme.get("source"),
        "methodClaimIds": relationship_theme.get("methodClaimIds") or [],
    }


def append_context_sentence(text: Any, sentence: Any) -> str:
    base = sanitize_public_answer_text(text)
    extra = sanitize_public_answer_text(sentence)
    if not extra or extra in base:
        return base
    if not base:
        return extra
    return normalize_zh_text(f"{base} {extra}")


def normal_user_contact_variant(status_key: str) -> str:
    if status_key == "blocked":
        return "blocked"
    if status_key == "no-contact":
        return "no-contact"
    if status_key in {"occasional-contact", "still-in-contact", "living-or-working-together"}:
        return "live"
    return "default"


def normal_user_direct_answer(question_key: str, status_key: str) -> str:
    options = NORMAL_USER_DIRECT_ANSWERS.get(question_key) or NORMAL_USER_DIRECT_ANSWERS["still-love-me"]
    variant = normal_user_contact_variant(status_key)
    return sanitize_public_answer_text(options.get(variant) or options.get("default"))


def normal_user_question_reason(question_key: str) -> str:
    if question_key == "still-love-me":
        return "所以重點是看他有沒有持續、自然、可觀察的回應。"
    if question_key == "any-chance":
        return "所以重點是互動能不能變輕、舊模式有沒有停下來。"
    if question_key == "when-to-contact":
        return "所以時機要看現在開口會不會讓壓力更重。"
    if question_key == "what-did-i-do-wrong":
        return "所以重點是找出哪一段互動可以改得比較輕。"
    if question_key == "stay-or-let-go":
        return "所以重點是這段互動有沒有讓你比較安心。"
    return "所以要回到可觀察的互動，不用單一反應下最後結論。"


def normal_user_why(question_key: str, relationship_theme: dict[str, Any] | None) -> str:
    theme_key = str((relationship_theme or {}).get("themeKey") or "")
    theme_reason = sanitize_public_answer_text(NORMAL_USER_THEME_REASONS.get(theme_key))
    if theme_reason:
        return theme_reason
    return normal_user_question_reason(question_key)


def normal_user_watch_items(
    *,
    question_key: str,
    relationship_theme: dict[str, Any] | None,
    emotional_risk: str | None = None,
) -> list[str]:
    items = [sanitize_public_answer_text(item) for item in NORMAL_USER_QUESTION_WATCH.get(question_key, [])]
    theme_key = str((relationship_theme or {}).get("themeKey") or "")
    theme_watch = sanitize_public_answer_text(NORMAL_USER_THEME_WATCH.get(theme_key))
    if theme_watch:
        items.append(theme_watch)
    risk_watch = sanitize_public_answer_text(NORMAL_USER_RISK_MODIFIERS.get(str(emotional_risk or "")))
    if risk_watch:
        items.append(risk_watch)
    return unique_strings([item for item in items if item])[:3]


def normal_user_next_step(
    *,
    question_key: str,
    contact_policy: dict[str, Any],
    timing_guidance: dict[str, Any],
    relationship_theme: dict[str, Any] | None,
    emotional_risk: str | None = None,
) -> str:
    status_key = str(contact_policy.get("statusKey") or "")
    contact_step = sanitize_public_answer_text(NORMAL_USER_NEXT_STEPS.get(status_key) or contact_policy.get("contactInstruction"))
    question_contact_step = sanitize_public_answer_text(NORMAL_USER_QUESTION_NEXT_STEPS.get((question_key, status_key)))
    timing_next = sanitize_public_answer_text(timing_guidance.get("nextMove"))
    risk_step = sanitize_public_answer_text(NORMAL_USER_RISK_MODIFIERS.get(str(emotional_risk or "")))
    if status_key == "blocked":
        return contact_step
    if question_contact_step:
        return append_context_sentence(question_contact_step, risk_step)
    if question_key == "when-to-contact" and timing_next:
        return append_context_sentence(timing_next, risk_step)
    if contact_step:
        return append_context_sentence(contact_step, risk_step)
    return append_context_sentence(timing_next or "先看下一個可觀察回應，再決定要不要行動。", risk_step)


def normal_user_stop_line(question_key: str, contact_policy: dict[str, Any]) -> str:
    status_key = str(contact_policy.get("statusKey") or "")
    if status_key in NORMAL_USER_STOP_LINES:
        return sanitize_public_answer_text(NORMAL_USER_STOP_LINES[status_key])
    if question_key == "still-love-me":
        return "不要用追問來證明他在不在意，也不要替他宣告內心。"
    if question_key == "any-chance":
        return "不要把一次回覆或一次熱絡，直接當成復合保證。"
    if question_key == "when-to-contact":
        return "不要連續補訊息，也不要把開口變成要對方立刻回答關係。"
    if question_key == "what-did-i-do-wrong":
        return "不要用自責換靠近，也不要把他的退開全部算成你的錯。"
    if question_key == "stay-or-let-go":
        return "如果他沒有自然延續，就先停下來，不要再用等待逼自己撐。"
    return "不要把單一星盤訊號寫成最後結果。"


def normal_user_evidence_bridge(
    *,
    question_key: str,
    contact_policy: dict[str, Any],
    timing_guidance: dict[str, Any],
    relationship_theme: dict[str, Any] | None,
) -> str:
    theme_label = repeated_theme_context_value(relationship_theme, "label")
    status_label = sanitize_public_answer_text(contact_policy.get("statusLabel"))
    timing_headline = sanitize_public_answer_text((timing_guidance.get("readableInterpretation") or {}).get("headline"))
    parts = unique_strings([theme_label, status_label, timing_headline])
    if not parts:
        return "這個判斷來自合盤互動、現實聯絡狀態和當下時機一起看。"
    if question_key == "when-to-contact":
        return normalize_zh_text(f"這個判斷會同時看：{'、'.join(parts[:3])}；所以只給開口方式，不給指定日期。")
    return normalize_zh_text(f"這個判斷會同時看：{'、'.join(parts[:3])}；所以不只用單一反應下結論。")


def normal_user_answer_payload(
    *,
    answer_layer: dict[str, Any],
    question_key: str,
    question_label: str,
    stage_key: str,
    contact_policy: dict[str, Any],
    timing_guidance: dict[str, Any],
    relationship_theme: dict[str, Any] | None = None,
    source_claim_ids: list[str] | None = None,
    question_selector: dict[str, Any] | None = None,
    emotional_risk: str | None = None,
) -> dict[str, Any]:
    selector = selector_trace_payload(question_selector or answer_layer.get("questionSelector"), question_key=question_key)
    direct_answer = normal_user_direct_answer(question_key, str(contact_policy.get("statusKey") or ""))
    why = normal_user_why(question_key, relationship_theme)
    watch_items = normal_user_watch_items(
        question_key=question_key,
        relationship_theme=relationship_theme,
        emotional_risk=emotional_risk,
    )
    next_step = normal_user_next_step(
        question_key=question_key,
        contact_policy=contact_policy,
        timing_guidance=timing_guidance,
        relationship_theme=relationship_theme,
        emotional_risk=emotional_risk,
    )
    stop_line = normal_user_stop_line(question_key, contact_policy)
    evidence_bridge = normal_user_evidence_bridge(
        question_key=question_key,
        contact_policy=contact_policy,
        timing_guidance=timing_guidance,
        relationship_theme=relationship_theme,
    )
    blocks = [
        {"key": "directAnswer", "label": NORMAL_USER_BLOCK_LABELS["directAnswer"], "body": direct_answer},
        {"key": "whyThisMatters", "label": NORMAL_USER_BLOCK_LABELS["whyThisMatters"], "body": why},
        {"key": "whatToWatch", "label": NORMAL_USER_BLOCK_LABELS["whatToWatch"], "items": watch_items},
        {"key": "nextStep", "label": NORMAL_USER_BLOCK_LABELS["nextStep"], "body": next_step},
        {"key": "stopLine", "label": NORMAL_USER_BLOCK_LABELS["stopLine"], "body": stop_line},
    ]
    return {
        "version": "normal-user-answer-v1",
        "questionKey": question_key,
        "questionLabel": question_label,
        "stageKey": stage_key,
        "contactStatusKey": contact_policy.get("statusKey"),
        "tone": str(emotional_risk or "calm"),
        "headline": sanitize_public_answer_text(NORMAL_USER_HEADLINES.get(question_key) or question_label),
        "directAnswer": direct_answer,
        "whyThisMatters": why,
        "whatToWatch": watch_items,
        "nextStep": next_step,
        "stopLine": stop_line,
        "evidenceBridge": evidence_bridge,
        "blocks": blocks,
        "relationshipTheme": relationship_theme or {},
        "sourceTraceIds": unique_strings([
            *(source_claim_ids or []),
            *((relationship_theme or {}).get("methodClaimIds") or []),
            *(selector.get("methodClaimIds") or []),
        ]),
        "methodClaimIds": selector.get("methodClaimIds") or [],
        "evidenceClusterKeys": selector.get("evidenceClusterKeys") or [],
        "questionSelector": selector,
    }


def question_stage_context(*, question_key: str, stage_key: str) -> str:
    if question_key == "when-to-contact":
        return "先看互動能不能承受新訊息，再決定要不要開口。"
    if question_key == "what-did-i-do-wrong":
        return "先把自責收小，找出可以調整的互動循環。"
    if question_key == "stay-or-let-go":
        return "先看這段關係有沒有回到穩定，再做最後決定。"
    if question_key == "any-chance":
        return "先看互動還能不能變輕、變穩，再談能不能重新靠近。"
    if stage_key == "broke-up-recent":
        return "剛分開時情緒還在震盪，越想立刻確認，互動越容易變緊。"
    if stage_key == "broke-up-long":
        return "距離拉長後，重點是重新建立輕量互動，先不用追回舊答案。"
    if stage_key == "crisis":
        return "危機期先把動作收小，避開在情緒最高點逼出結論。"
    return "先把互動拉回比較能回應的狀態。"


def answer_next_move(
    *,
    question_key: str,
    stage_key: str,
    answer_layer: dict[str, Any],
    contact_policy: dict[str, Any],
    timing_guidance: dict[str, Any],
    relationship_theme: dict[str, Any] | None = None,
) -> str:
    timing_next = str(timing_guidance.get("nextMove") or "").strip()
    action_scale = contact_policy.get("actionScale")
    if action_scale == 0:
        return "先尊重已經關上的聯絡邊界，不要用其他方式繞過對方。"
    if question_key == "when-to-contact" and timing_next:
        return sanitize_public_answer_text(timing_next)
    therefore = sanitize_public_answer_text(answer_layer.get("therefore"))
    if therefore:
        if question_key == "still-love-me":
            therefore = therefore.replace("壓力", "緊繃感")
        return therefore
    return question_stage_context(question_key=question_key, stage_key=stage_key)


def primary_answer_body(question_key: str, body: Any) -> str:
    answer = sanitize_public_answer_text(body)
    if not answer:
        answer = "這題要先回到星盤證據、現實聯絡狀態和當下節奏一起看，再判斷單一反應代表什麼。"
    frame = QUESTION_PRIMARY_ANSWER_FRAMES.get(question_key, "")
    if frame and frame.rstrip("：") not in answer:
        return normalize_zh_text(f"{frame}{answer}")
    return normalize_zh_text(answer)


def question_evidence_title_config(question_key: str) -> dict[str, Any]:
    return QUESTION_EVIDENCE_HIGHLIGHT_TITLES.get(question_key) or {
        "theme": "重複關係主題",
        "contact": "現實聯絡狀態",
        "timing": "目前時機狀態",
        "evidence": ["判斷線索 1", "判斷線索 2", "判斷線索 3"],
    }


def question_contact_highlight_body(question_key: str, status_label: str) -> str:
    status = sanitize_public_answer_text(status_label)
    if question_key == "still-love-me":
        return normalize_zh_text(f"{status}；所以要看回應是否穩定，把沉默和一次回覆放回整體互動裡判斷。")
    if question_key == "any-chance":
        return normalize_zh_text(f"{status}；機會要看能不能自然接上，也要看對話是否真的變輕。")
    if question_key == "when-to-contact":
        return normalize_zh_text(f"{status}；這會決定能不能開口、訊息要多輕，以及送出後要不要停下來。")
    if question_key == "what-did-i-do-wrong":
        return normalize_zh_text(f"{status}；它說明互動狀態，幫你把責任拆回具體事件。")
    if question_key == "stay-or-let-go":
        return normalize_zh_text(f"{status}；這會影響你要不要繼續等，也提醒你照顧自己的消耗。")
    return status


def question_timing_highlight_body(question_key: str, timing_headline: str) -> str:
    headline = sanitize_public_answer_text(timing_headline)
    if question_key == "still-love-me":
        return normalize_zh_text(f"{headline}；短期氣氛用來輔助判斷回應是否能變穩。")
    if question_key == "any-chance":
        return normalize_zh_text(f"{headline}；時機用來判斷修復步調和適合的行動大小。")
    if question_key == "when-to-contact":
        return normalize_zh_text(f"{headline}；這裡判斷開口方式和適合的月份區間。")
    if question_key == "what-did-i-do-wrong":
        return normalize_zh_text(f"{headline}；先讓情緒降溫，再看哪一段互動真的可以調整。")
    if question_key == "stay-or-let-go":
        return normalize_zh_text(f"{headline}；先觀察有沒有穩定行動，再決定要等、談，還是退開。")
    return headline


def answer_evidence_highlights(
    *,
    answer_layer: dict[str, Any],
    question_key: str,
    contact_policy: dict[str, Any],
    timing_guidance: dict[str, Any],
    relationship_theme: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    highlights: list[dict[str, str]] = []
    titles = question_evidence_title_config(question_key)
    theme_label = repeated_theme_context_value(relationship_theme, "label")
    theme_body = repeated_theme_context_value(relationship_theme, "answerFocus")
    if theme_label and theme_body:
        highlights.append(
            {
                "key": "repeated-relationship-theme",
                "title": normalize_zh_text(f"{titles.get('theme') or '重複關係主題'}：{theme_label}"),
                "body": theme_body,
            }
        )
    status_label = sanitize_public_answer_text(contact_policy.get("statusLabel"))
    if status_label:
        highlights.append(
            {
                "key": "contact-boundary",
                "title": str(titles.get("contact") or "現實聯絡狀態"),
                "body": question_contact_highlight_body(question_key, status_label),
            }
        )
    timing_readable = timing_guidance.get("readableInterpretation") or {}
    timing_headline = sanitize_public_answer_text(timing_readable.get("headline"))
    if timing_headline:
        highlights.append(
            {
                "key": "timing-rhythm",
                "title": str(titles.get("timing") or "目前時機狀態"),
                "body": question_timing_highlight_body(question_key, timing_headline),
            }
        )
    because_items = [
        sanitize_public_answer_text(item)
        for item in answer_layer.get("because") or []
        if sanitize_public_answer_text(item)
    ]
    if theme_label and theme_body:
        because_items = [
            item
            for item in because_items
            if not (
                item == theme_body
                or item.startswith(f"重複主題：{theme_label}")
                or (theme_label in item and theme_body in item)
            )
        ]
    evidence_titles = [str(item) for item in titles.get("evidence") or [] if item]
    for index, body in enumerate(because_items[:3], start=1):
        title = evidence_titles[index - 1] if index <= len(evidence_titles) else f"判斷線索 {index}"
        highlights.append(
            {
                "key": f"evidence-{index}",
                "title": title,
                "body": body,
            }
        )
    return highlights[:5]


def answer_guidance_readable_interpretation(
    *,
    answer_layer: dict[str, Any],
    question_key: str,
    question_label: str,
    stage_key: str,
    contact_policy: dict[str, Any],
    timing_guidance: dict[str, Any],
    relationship_theme: dict[str, Any] | None = None,
    source_claim_ids: list[str] | None = None,
    question_selector: dict[str, Any] | None = None,
) -> ReadableInterpretation:
    body = primary_answer_body(question_key, answer_layer.get("shortAnswer"))
    selector = selector_trace_payload(question_selector or answer_layer.get("questionSelector"), question_key=question_key)
    return {
        "version": "readable-interpretation-v1",
        "module": "question_answer",
        "locale": "zh-TW",
        "headline": QUESTION_ANSWER_HEADLINES.get(question_key, "先把問題放回可觀察證據"),
        "meaning": QUESTION_FOCUS_MEANINGS.get(question_key, f"這一段直接回答「{question_label}」，但不做絕對預測。"),
        "body": body,
        "nextMove": answer_next_move(
            question_key=question_key,
            stage_key=stage_key,
            answer_layer=answer_layer,
            contact_policy=contact_policy,
            timing_guidance=timing_guidance,
            relationship_theme=relationship_theme,
        ),
        "caution": QUESTION_ANSWER_CAUTIONS.get(question_key, "答案只能根據現有條件判斷，不能把星盤寫成保證。"),
        "sourceClaimIds": source_claim_ids or [],
        "methodClaimIds": selector.get("methodClaimIds") or [],
        "evidenceClusterKeys": selector.get("evidenceClusterKeys") or [],
        "questionSelector": selector,
        "debug": {
            "questionKey": question_key,
            "stageKey": stage_key,
            "ruleId": answer_layer.get("ruleId"),
            "ruleConfidence": answer_layer.get("ruleConfidence"),
            "repeatedThemeKey": (relationship_theme or {}).get("themeKey") if isinstance(relationship_theme, dict) else None,
        },
    }


def answer_guidance_payload(
    *,
    answer_layer: dict[str, Any],
    question_key: str,
    question_label: str,
    stage_key: str,
    contact_policy: dict[str, Any],
    timing_guidance: dict[str, Any],
    relationship_theme: dict[str, Any] | None = None,
    source_claim_ids: list[str] | None = None,
    question_selector: dict[str, Any] | None = None,
    emotional_risk: str | None = None,
) -> dict[str, Any]:
    selector = selector_trace_payload(question_selector or answer_layer.get("questionSelector"), question_key=question_key)
    readable = answer_guidance_readable_interpretation(
        answer_layer=answer_layer,
        question_key=question_key,
        question_label=question_label,
        stage_key=stage_key,
        contact_policy=contact_policy,
        timing_guidance=timing_guidance,
        relationship_theme=relationship_theme,
        source_claim_ids=source_claim_ids,
        question_selector=selector,
    )
    normal_user_answer = normal_user_answer_payload(
        answer_layer=answer_layer,
        question_key=question_key,
        question_label=question_label,
        stage_key=stage_key,
        contact_policy=contact_policy,
        timing_guidance=timing_guidance,
        relationship_theme=relationship_theme,
        source_claim_ids=source_claim_ids,
        question_selector=selector,
        emotional_risk=emotional_risk,
    )
    return {
        "version": "answer-guidance-v1",
        "questionKey": question_key,
        "questionLabel": question_label,
        "ruleId": answer_layer.get("ruleId"),
        "ruleConfidence": answer_layer.get("ruleConfidence"),
        "shortAnswer": readable.get("body"),
        "evidenceHighlights": answer_evidence_highlights(
            answer_layer=answer_layer,
            question_key=question_key,
            contact_policy=contact_policy,
            timing_guidance=timing_guidance,
            relationship_theme=relationship_theme,
        ),
        "nextMove": readable.get("nextMove"),
        "relationshipTheme": relationship_theme or {},
        "questionSelector": selector,
        "methodClaimIds": selector.get("methodClaimIds") or [],
        "evidenceClusterKeys": selector.get("evidenceClusterKeys") or [],
        "readableInterpretation": readable,
        "normalUserAnswer": normal_user_answer,
    }


def reason_next_move(label: str, question_key: str) -> str:
    if question_key == "any-chance":
        if "卡住" in label:
            return "先看這個模式能不能停下來，不要用同一種靠近方式再試一次。"
        if "重啟" in label:
            return "只看對方有沒有自然接住，不要把一次回覆放大成復合。"
        if "修復" in label:
            return "先看互動能不能自然接上，不要立刻推到復合或承諾。"
    if "牽動" in label or "在意" in label or "靠近" in label or "修復" in label:
        return "先把它當成觀察線索，不要立刻推到復合或承諾。"
    if "壓力" in label or "防衛" in label or "門檻" in label or "壓住" in label:
        return "先讓訊息和情緒都變輕，再看對方能不能自然回應。"
    if "焦慮" in label or "自責" in label or "保護" in label:
        return "先穩住自己的步調，不用追問、長文或過度道歉換安全感。"
    if question_key == "when-to-contact":
        return "如果要開口，只用一句短、輕、沒有要求的訊息。"
    if question_key == "still-love-me":
        return "先看對方是否有穩定回應，不用追問來證明他在不在意。"
    if question_key == "what-did-i-do-wrong":
        return "先找一個能調整的互動方式，不用把整段關係都變成你的錯。"
    if question_key == "stay-or-let-go":
        return "用對方是否有穩定行動來判斷，不用一句話決定全部。"
    return "把這個點放進接下來幾天的互動觀察，先不下最後結論。"


def chance_headline(value: int, question_key: str) -> str:
    if question_key == "when-to-contact":
        return "可以看開口時機，但這裡不指定哪一天"
    if question_key == "stay-or-let-go":
        return "重點不是有沒有感覺，而是這段關係會不會讓你更累"
    if value >= 75:
        return "有條件可以慢慢靠近"
    if value >= 58:
        return "還有機會，但要先讓互動變穩"
    return "先看現實回應，不適合硬推"


def chance_next_move(question_key: str, stage_key: str) -> str:
    if question_key == "when-to-contact":
        return "先等自己不是為了立刻要答案，再考慮一句短而不追問的訊息。"
    if question_key == "what-did-i-do-wrong":
        return "先修一個看得見的表達方式，不用一次扛下整段關係。"
    if question_key == "stay-or-let-go":
        return "先看互動是否真的變穩，再決定要等、談，還是退開。"
    if question_key == "any-chance" or stage_key == "broke-up-long":
        return "如果要重新靠近，先用沒有要求、對方容易接住的方式開始。"
    return "先把動作收小，看對方是否能自然回應。"


def timeline_next_move(title: str) -> str:
    if "不要" in title or "不主動" in title or "停止" in title or "保持距離" in title:
        return "這一步先保護自己的步調，不要再讓互動變更緊。"
    if "觀察" in title or "看" in title:
        return "這一步只觀察回應，不用把一個反應當成全部答案。"
    if "訊息" in title or "談話" in title or "測試" in title or "切入" in title or "開口" in title:
        return "這一步只說輕一點的一句話，讓對方有空間自然回應。"
    return "這一步只做一件小事，讓話題保留退路。"


def thought_readable_interpretation(
    *,
    body: str,
    index: int,
    question_key: str,
    stage_key: str,
    source_claim_ids: list[str] | None = None,
    question_selector: dict[str, Any] | None = None,
) -> ReadableInterpretation:
    selector = selector_trace_payload(question_selector, question_key=question_key)
    return {
        "version": "readable-interpretation-v1",
        "module": "question_thought",
        "locale": "zh-TW",
        "headline": f"先看第{zh_order(index)}個重點",
        "meaning": QUESTION_FOCUS_MEANINGS.get(question_key, "這一段先把問題放回關係互動，不做絕對判斷。"),
        "body": normalize_zh_text(body),
        "nextMove": question_stage_context(question_key=question_key, stage_key=stage_key),
        "sourceClaimIds": source_claim_ids or [],
        "methodClaimIds": selector.get("methodClaimIds") or [],
        "evidenceClusterKeys": selector.get("evidenceClusterKeys") or [],
        "questionSelector": selector,
        "debug": {"questionKey": question_key, "stageKey": stage_key, "index": index},
    }


def reason_card_readable_interpretation(
    *,
    label: str,
    body: str,
    value: int,
    question_key: str,
    stage_key: str,
    source_claim_ids: list[str] | None = None,
    question_selector: dict[str, Any] | None = None,
) -> ReadableInterpretation:
    selector = selector_trace_payload(question_selector, question_key=question_key)
    return {
        "version": "readable-interpretation-v1",
        "module": "question_reason",
        "locale": "zh-TW",
        "headline": label,
        "meaning": QUESTION_FOCUS_MEANINGS.get(question_key, "這張卡用來解釋目前互動卡住的主要原因。"),
        "body": normalize_zh_text(body),
        "nextMove": reason_next_move(label, question_key),
        "caution": "分數表示條件強弱，還要搭配對方後續行動一起看。",
        "sourceClaimIds": source_claim_ids or [],
        "methodClaimIds": selector.get("methodClaimIds") or [],
        "evidenceClusterKeys": selector.get("evidenceClusterKeys") or [],
        "questionSelector": selector,
        "debug": {"questionKey": question_key, "stageKey": stage_key, "value": value},
    }


def chance_readable_interpretation(
    *,
    value: int,
    notes: list[str],
    question_key: str,
    stage_key: str,
    source_claim_ids: list[str] | None = None,
    question_selector: dict[str, Any] | None = None,
) -> ReadableInterpretation:
    selector = selector_trace_payload(question_selector, question_key=question_key)
    return {
        "version": "readable-interpretation-v1",
        "module": "question_chance",
        "locale": "zh-TW",
        "headline": chance_headline(value, question_key),
        "meaning": "能不能重新靠近，取決於條件、步調和現實承受度。",
        "body": normalize_zh_text("".join(note.strip() for note in notes if note)),
        "nextMove": chance_next_move(question_key, stage_key),
        "caution": "機會需要看後續回應是否穩定；聯絡時機用區間和節奏判斷。",
        "sourceClaimIds": source_claim_ids or [],
        "methodClaimIds": selector.get("methodClaimIds") or [],
        "evidenceClusterKeys": selector.get("evidenceClusterKeys") or [],
        "questionSelector": selector,
        "debug": {"questionKey": question_key, "stageKey": stage_key, "value": value},
    }


def timeline_step_readable_interpretation(
    *,
    range_label: str,
    title: str,
    body: str,
    question_key: str,
    stage_key: str,
    source_claim_ids: list[str] | None = None,
    question_selector: dict[str, Any] | None = None,
) -> ReadableInterpretation:
    selector = selector_trace_payload(question_selector, question_key=question_key)
    return {
        "version": "readable-interpretation-v1",
        "module": "question_timeline",
        "locale": "zh-TW",
        "headline": f"{zh_timeline_range(range_label)}：{title}",
        "meaning": "這是接下來幾天的行動順序，不是占星保證或硬性期限。",
        "body": normalize_zh_text(body),
        "nextMove": timeline_next_move(title),
        "sourceClaimIds": source_claim_ids or [],
        "methodClaimIds": selector.get("methodClaimIds") or [],
        "evidenceClusterKeys": selector.get("evidenceClusterKeys") or [],
        "questionSelector": selector,
        "debug": {"questionKey": question_key, "stageKey": stage_key, "range": range_label},
    }


def boundary_readable_interpretation(
    *,
    body: str,
    index: int,
    question_key: str,
    stage_key: str,
    source_claim_ids: list[str] | None = None,
    question_selector: dict[str, Any] | None = None,
) -> ReadableInterpretation:
    selector = selector_trace_payload(question_selector, question_key=question_key)
    return {
        "version": "readable-interpretation-v1",
        "module": "question_boundary",
        "locale": "zh-TW",
        "headline": f"先不要做的第{zh_order(index)}件事",
        "meaning": "這一段幫你避開會讓互動越推越緊的做法。",
        "body": normalize_zh_text(body),
        "nextMove": question_stage_context(question_key=question_key, stage_key=stage_key),
        "caution": "如果你已經很焦慮，先不要用新的訊息尋求立刻安撫。",
        "sourceClaimIds": source_claim_ids or [],
        "methodClaimIds": selector.get("methodClaimIds") or [],
        "evidenceClusterKeys": selector.get("evidenceClusterKeys") or [],
        "questionSelector": selector,
        "debug": {"questionKey": question_key, "stageKey": stage_key, "index": index},
    }


CONTACT_ACTION_TEMPLATES: dict[str, dict[str, str]] = {
    "blocked": {
        "headline": "先不要聯絡",
        "meaning": "現實上能不能安全開口，以及界線要怎麼守住，必須放在一起判斷。",
        "body": "對方已經關上聯絡方式時，現在能做的是停下追問、不繞路找他，先守住彼此的界線。",
        "nextMove": "不要換帳號、不要請別人傳話，也不要用長訊息突破界線。",
        "caution": "先尊重對方已經畫出的邊界，把注意力放回自己的穩定。",
    },
    "no-contact": {
        "headline": "先觀察，再決定要不要開口",
        "meaning": "目前有沒有自然說話的空間，要和界線及訊息大小一起判斷。",
        "body": "完全沒有聯絡時，目前只適合很小、很輕地試一次。除非後面真的出現比較自然的回應，否則不要用訊息追答案。",
        "nextMove": "如果要開口，只適合一句短、輕、沒有要求的訊息；送出後先停下來看反應。",
        "caution": "不要把一次訊息當成最後答案；對方有沒有自然接住，才是接下來要看的事。",
    },
    "occasional-contact": {
        "headline": "跟著回應走，不要加速",
        "meaning": "偶爾回覆代表還有一點互動空間，先把它當成低強度訊號。",
        "body": "你們還能說上一點話，但目前不適合把話題推太滿。把話說短、說清楚，讓對方有餘地接住或停下。",
        "nextMove": "回覆變穩前，不要把一次回應放大成復合訊號。",
        "caution": "看回應是否持續，比追問對方心裡怎麼想更重要。",
    },
    "still-in-contact": {
        "headline": "在原本對話裡放輕",
        "meaning": "你們還能聊天時，重點是讓原本的對話恢復到比較接得住的狀態。",
        "body": "不要另外找一個日子逼出答案。先在原本的對話裡把語氣放輕，讓互動重新變得比較自然。",
        "nextMove": "先聊一件具體、簡短、沒有逼問的事，觀察對方會不會自然接住。",
        "caution": "能聊天不等於已經能談復合；先讓對話穩下來。",
    },
    "living-or-working-together": {
        "headline": "先保護共同場域",
        "meaning": "你們還會見到或有共同場域時，場合本身也會影響對方怎麼反應。",
        "body": "不適合把共同場合變成感情攤牌。先維持普通、自然、可退場，讓對方不用被迫立刻回應。",
        "nextMove": "不要在共同場域逼談關係；先把互動維持在禮貌、穩定、不中斷日常。",
        "caution": "共同場域裡最重要的是保留退路，不讓任何一方被迫表態。",
    },
    "unknown": {
        "headline": "先補足現實狀態",
        "meaning": "聯絡情境不清楚時，這份解讀不能直接建議主動靠近。",
        "body": "先確認目前是否真的有可以自然開口的通道，再決定要靠近、觀察，還是先暫停。",
        "nextMove": "先釐清你們現在能不能正常聯絡，再判斷下一步。",
        "caution": "沒有現實狀態時，星盤不應該替你做出主動聯絡的結論。",
    },
}


CONTACT_ACTION_QUESTION_VARIANTS: dict[str, tuple[str, ...]] = {
    "still-love-me": (
        "這題先不要逼他說感覺，先看他會不會自然延續一次小互動。",
        "你要看的不是一句表態，而是他是否不用你追問也會把話接下去。",
        "如果只有被動回覆，先不要把它放大成投入。",
    ),
    "any-chance": (
        "這題要看舊循環有沒有變小，所以行動不能又把壓力推回原點。",
        "先把機會拆成小互動，不用一次談到復合或承諾。",
        "真正有用的是讓下一次互動比前一次更穩。",
    ),
    "when-to-contact": (
        "你問的是能不能開口，所以重點是訊息大小和對方能不能自然停下。",
        "開口前先確認自己不是想用一句話逼出完整答案。",
        "如果要聯絡，只做對方可以輕鬆接住的小動作。",
    ),
    "what-did-i-do-wrong": (
        "這題先不要把錯全攬回自己，行動只改一個具體互動環節。",
        "你可以修正說法，但不用用自責去追一個答案。",
        "先看哪種表達會讓對話清楚一點，而不是更重。",
    ),
    "stay-or-let-go": (
        "這題要保護你的消耗感，行動只用來看關係有沒有變穩。",
        "如果下一步讓你更累，就先不要把等待繼續放大。",
        "留下或放下都先看現實反應，不只看你有多捨不得。",
    ),
}

CONTACT_ACTION_STAGE_VARIANTS: dict[str, tuple[str, ...]] = {
    "broke-up-recent": (
        "剛分開不久時，先不要讓情緒帶著動作跑太快。",
        "分開初期容易把每個回應放大，所以要看連續反應。",
    ),
    "broke-up-long": (
        "時間已經拉開時，牽動感需要用新的行動來驗證。",
        "分開一段時間後，不要只靠回憶判斷現在。",
    ),
    "cold-war": (
        "冷戰時最容易互等對方先低頭，所以語氣要先放軟。",
        "現在先讓小互動能被接住，先不討論誰錯。",
    ),
    "crisis": (
        "關係緊繃時，先不要把所有問題壓在同一次對話。",
        "危機期先降低傷害，再看有沒有修復空間。",
    ),
}

CONTACT_ACTION_THEME_VARIANTS: dict[str, tuple[str, ...]] = {
    "emotional_safety": (
        "因為主題牽涉安全感，行動要先讓不安下降。",
        "安全感不穩時，不要用追問換安心。",
    ),
    "saturn_pressure": (
        "因為主題牽涉責任壓力，先不要一次談到承諾。",
        "壓力偏重時，先把問題拆小。",
    ),
    "communication_repair": (
        "因為主題牽涉說法，先讓句子變短、重點變清楚。",
        "溝通卡住時，少說一點反而比較能讓對話回來。",
    ),
    "attraction_pursuit": (
        "因為主題牽涉火花，先讓熱絡回到日常，不立刻定義關係。",
        "有靠近感時，先看它能不能自然延續。",
    ),
    "action_conflict": (
        "因為主題牽涉步調，一急就容易變硬，所以先把動作收小。",
        "動作要比情緒小，才不會又推成衝突。",
    ),
    "identity_rhythm": (
        "因為主題牽涉尊重感，先保留彼此台階。",
        "不要把下一步變成誰先低頭。",
    ),
    "outer_intensity": (
        "因為主題牽涉強烈感受，先回到現實反應。",
        "感覺越強，越不能只靠想像補答案。",
    ),
}


def stable_pick(options: tuple[str, ...], seed: str) -> str:
    if not options:
        return ""
    return options[sum(ord(char) for char in seed) % len(options)]


def contact_action_variant_copy(
    *,
    question_key: str,
    stage_key: str,
    theme_key: str,
    status_key: str,
    seed: str,
) -> dict[str, str]:
    question_line = stable_pick(CONTACT_ACTION_QUESTION_VARIANTS.get(question_key) or (), f"{seed}:question")
    stage_line = stable_pick(CONTACT_ACTION_STAGE_VARIANTS.get(stage_key) or (), f"{seed}:stage")
    theme_line = stable_pick(CONTACT_ACTION_THEME_VARIANTS.get(theme_key) or (), f"{seed}:theme")
    status_tail = {
        "blocked": "這一步的目的不是讓對方回來，而是讓界線先清楚。",
        "no-contact": "送出或不送出，都不要連續加碼。",
        "occasional-contact": "先讓回覆自然變穩，再決定要不要多說一點。",
        "still-in-contact": "能聊天時也要留有停下的空間。",
        "living-or-working-together": "共同場域要先能自然相處，才有後面的可能。",
    }.get(status_key, "")
    return {
        "bodyTail": join_zh_sentences(question_line, stage_line),
        "nextTail": join_zh_sentences(theme_line, status_tail),
        "cautionTail": theme_line,
    }


def contact_action_readable_interpretation(
    *,
    contact_policy: dict[str, Any],
    question_key: str,
    stage_key: str,
    relationship_theme: dict[str, Any] | None = None,
    source_claim_ids: list[str] | None = None,
    question_selector: dict[str, Any] | None = None,
) -> ReadableInterpretation:
    status_key = str(contact_policy.get("statusKey") or "unknown")
    template = CONTACT_ACTION_TEMPLATES.get(status_key) or CONTACT_ACTION_TEMPLATES["unknown"]
    claim_ids = source_claim_ids or []
    selector = selector_trace_payload(question_selector, question_key=question_key)
    theme_key = str((relationship_theme or {}).get("themeKey") or "")
    variant = contact_action_variant_copy(
        question_key=question_key,
        stage_key=stage_key,
        theme_key=theme_key,
        status_key=status_key,
        seed=f"{status_key}:{question_key}:{stage_key}:{theme_key}",
    )
    theme_label = repeated_theme_context_value(relationship_theme, "label")
    theme_caution = ""
    if theme_label:
        theme_caution = f"同時因為合盤重複主題是「{theme_label}」，行動建議要先服務這個模式，避免只照你想不想聯絡來走。"
    return {
        "version": "readable-interpretation-v1",
        "module": "question_action",
        "locale": "zh-TW",
        "headline": normalize_zh_text(template["headline"]),
        "meaning": normalize_zh_text(template["meaning"]),
        "body": sanitize_public_answer_text(join_zh_sentences(template["body"], variant["bodyTail"])),
        "nextMove": sanitize_public_answer_text(join_zh_sentences(template["nextMove"], variant["nextTail"])),
        "caution": append_context_sentence(join_zh_sentences(template["caution"], variant["cautionTail"]), theme_caution),
        "sourceClaimIds": claim_ids,
        "methodClaimIds": selector.get("methodClaimIds") or [],
        "evidenceClusterKeys": selector.get("evidenceClusterKeys") or [],
        "questionSelector": selector,
        "debug": {
            "questionKey": question_key,
            "stageKey": stage_key,
            "statusKey": status_key,
            "actionScale": contact_policy.get("actionScale"),
            "repeatedThemeKey": (relationship_theme or {}).get("themeKey") if isinstance(relationship_theme, dict) else None,
        },
    }


TIMING_SIGNAL_COPY: dict[str, dict[str, str]] = {
    "mercury": {
        "title": "水星：話能不能說清楚",
        "support": "比較支持短句、清楚、留有餘地的訊息。",
        "caution": "容易越講越緊，先不要辯論、補充太多，或急著修正對方。",
        "none": "目前沒有明顯溝通助力，訊息內容要更簡短。",
    },
    "venus": {
        "title": "金星：語氣能不能變柔和",
        "support": "比較支持釋放善意、修復氣氛，承諾仍要看後續穩定行動。",
        "caution": "柔和感不夠明顯，不適合用情緒很滿的方式靠近。",
        "none": "目前沒有明顯緩和助力，不要只靠感性話語推動關係。",
    },
    "mars": {
        "title": "火星：會不會太急",
        "support": "行動感存在，但仍要控速，不要把急迫當成方向。",
        "caution": "容易把焦急變成硬碰硬，先避開長文、追問或把關係題一次攤開。",
        "none": "沒有明顯火星刺激時，仍先維持原本壓力較輕的步調。",
    },
    "saturn": {
        "title": "土星：邊界會不會變硬",
        "support": "責任感和界線需要被尊重，慢一點反而比較穩。",
        "caution": "限制感、壓力或界線感變強，現在越逼越容易讓對話關上。",
        "none": "沒有明顯土星拉扯，但仍要尊重現實界線。",
    },
    "moon": {
        "title": "月亮：短期情緒起伏",
        "support": "情緒氣氛可以參考，但只能當輔助，不單獨決定行動。",
        "caution": "情緒起伏容易放大反應，先不要在不安最高時開口。",
        "none": "短期情緒訊號不明顯，先回到主要關係證據。",
    },
}


def timing_signal_state(cluster: dict[str, Any], support_flag: bool = False, caution_flag: bool = False) -> str:
    if caution_flag:
        return "caution"
    if support_flag or int(cluster.get("itemCount") or 0) > 0 or int(cluster.get("windowCount") or 0) > 0:
        return "support"
    return "none"


def timing_guidance_signals(
    *,
    timing_contact: dict[str, Any],
    timing_selectors: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    mercury_state = "caution" if timing_contact.get("hasMercuryCommunicationPressure") else (
        "support" if timing_contact.get("hasMercuryCommunicationWindow") else timing_signal_state(timing_selectors.get("timingMercuryCommunication") or {})
    )
    venus_state = "support" if timing_contact.get("hasVenusSofteningWindow") else timing_signal_state(timing_selectors.get("timingVenusSoftening") or {})
    mars_state = timing_signal_state(timing_selectors.get("timingMarsActivation") or {}, caution_flag=bool(timing_contact.get("hasMarsActivationRisk")))
    saturn_state = timing_signal_state(timing_selectors.get("timingSaturnPressure") or {}, caution_flag=bool(timing_contact.get("hasSaturnBoundaryRisk")))
    moon_state = timing_signal_state(timing_selectors.get("timingMoonWeather") or {})
    states = {
        "mercury": mercury_state,
        "venus": venus_state,
        "mars": mars_state,
        "saturn": saturn_state,
        "moon": moon_state,
    }
    output: list[dict[str, str]] = []
    for key, state in states.items():
        copy = TIMING_SIGNAL_COPY[key]
        output.append({"key": key, "title": copy["title"], "state": state, "body": copy[state]})
    return output


def timing_guidance_copy(
    *,
    timing_contact: dict[str, Any],
    timing_window: dict[str, Any],
    relationship_theme: dict[str, Any] | None = None,
) -> dict[str, str]:
    action = str(timing_contact.get("recommendedAction") or "not_calculated")
    has_mercury = bool(timing_contact.get("hasMercuryCommunicationWindow"))
    has_venus = bool(timing_contact.get("hasVenusSofteningWindow"))
    has_mars = bool(timing_contact.get("hasMarsActivationRisk"))
    has_saturn = bool(timing_contact.get("hasSaturnBoundaryRisk"))
    sample_count = int(timing_contact.get("sampleCount") or timing_window.get("sampleCount") or 0)

    theme_timing = repeated_theme_context_value(relationship_theme, "timingFocus")

    if action == "not_calculated" or sample_count <= 0:
        return {
            "headline": "先用當下狀態判斷，不排精準日",
            "meaning": "近期星象是否足以支持聯絡步調仍要確認；資料不足時，不會硬排日期。",
            "body": append_context_sentence("這次沒有足夠的短期掃描資料，所以時機判讀只能回到當下行運、互動負荷和聯絡情境。結論會保守：不要把某一天當成唯一機會。", theme_timing),
            "nextMove": "先照前面的聯絡尺度走，等互動變穩或補足時機資料後，再看能不能靠近。",
            "caution": "沒有足夠資料時，不應該把星象寫成精準聯絡日。",
        }
    if action == "avoid_push":
        if has_mars and has_saturn:
            headline = "先收小，避免把氣氛推緊"
            body = "這段時間比較容易一急就讓氣氛變緊；長文、追問或把關係題一次攤開，都可能讓對方更想退開。"
        elif has_mars:
            headline = "先避開衝動傳訊"
            body = "火星訊號變強時，焦急很容易變成硬碰硬。現在不適合長文、追問或立刻把關係題攤開。"
        elif has_saturn:
            headline = "先避開逼近邊界"
            body = "土星訊號變強時，責任、距離和界線比較敏感。越想要答案，越要先把問題縮到對方能回答的一小段。"
        else:
            headline = "先避開推進"
            body = "目前比較容易把靠近變成壓迫。現在不適合把關係一次攤開，也不適合連續補訊息。"
        return {
            "headline": headline,
            "meaning": "近期節奏能不能承受主動靠近，不代表對方一定會怎麼回。",
            "body": append_context_sentence(body, theme_timing),
            "nextMove": "先把聯絡停在不打擾的位置，等緊繃感下降，再看是否有自然回應。",
            "caution": "不要用時機感替衝動背書；越急越要先停。",
        }
    if action == "low_pressure_message":
        if has_mercury and has_venus:
            headline = "可以輕一點說，但不要要答案"
            body = "水星讓話比較容易說清楚，金星讓語氣比較柔和。這種時候適合短句、善意、能停下，不適合把關係題一次攤開。"
        elif has_mercury:
            headline = "可以用短句把話說清楚"
            body = "水星訊號比較支持清楚表達。重點是說一件小事，不要一次解釋完整段關係。"
        elif has_venus:
            headline = "可以柔和釋放善意"
            body = "金星訊號比較支持把語氣放軟，讓氣氛不那麼緊。但這只適合靠近一點，不適合直接要承諾。"
        else:
            headline = "可以輕一點靠近"
            body = "近期節奏有一點支持主動，但只能用很小、很容易退回的位置靠近。"
        return {
            "headline": headline,
            "meaning": "某種說法比較容易被接住，不代表結果有保證。",
            "body": append_context_sentence(body, theme_timing),
            "nextMove": "只發一個很短的訊息，內容放在近況或善意，不問復合、不要求立刻回。",
            "caution": "對方是否自然接住，比訊息寫得多完整更重要。",
        }
    if action == "observe_for_soft_window":
        return {
            "headline": "有柔和訊號，但先看對方反應",
            "meaning": "目前有一點可以放輕的條件，但還不到適合直接推進。",
            "body": append_context_sentence("水星或金星有一點支持，但整體還沒有穩到適合直接傳訊。先看對方是否自然接話，再決定要不要靠近。", theme_timing),
            "nextMove": "不要主動加速；如果對方有回應，再用短句延續，不把話題推到復合。",
            "caution": "有柔和訊號不等於可以立刻要答案。",
        }
    return {
        "headline": "目前先看現有互動，不主動推進",
        "meaning": "計算資料裡還沒有足夠支持主動傳訊的溝通或柔和訊號。",
        "body": append_context_sentence("目前適合先看現有互動，讓狀態變穩，比重新丟一個問題更重要。", theme_timing),
        "nextMove": "先看現有互動是否變穩；沒有自然回應前，先不要新增訊息。",
        "caution": "觀察不是無限等待，而是先避免把關係推得更緊。",
    }


def timing_guidance_readable_interpretation(
    *,
    timing_contact: dict[str, Any],
    timing_window: dict[str, Any],
    timing_selectors: dict[str, dict[str, Any]],
    question_key: str,
    stage_key: str,
    relationship_theme: dict[str, Any] | None = None,
    source_claim_ids: list[str] | None = None,
    question_selector: dict[str, Any] | None = None,
) -> ReadableInterpretation:
    copy = timing_guidance_copy(timing_contact=timing_contact, timing_window=timing_window, relationship_theme=relationship_theme)
    selector = selector_trace_payload(question_selector, question_key=question_key)
    dominant_signals = [
        item["key"]
        for item in timing_guidance_signals(timing_contact=timing_contact, timing_selectors=timing_selectors)
        if item["state"] != "none"
    ][:3]
    return {
        "version": "readable-interpretation-v1",
        "module": "question_timing",
        "locale": "zh-TW",
        "headline": normalize_zh_text(copy["headline"]),
        "meaning": normalize_zh_text(copy["meaning"]),
        "body": normalize_zh_text(copy["body"]),
        "nextMove": normalize_zh_text(copy["nextMove"]),
        "caution": normalize_zh_text(copy["caution"]),
        "sourceClaimIds": source_claim_ids or [],
        "methodClaimIds": selector.get("methodClaimIds") or [],
        "evidenceClusterKeys": selector.get("evidenceClusterKeys") or [],
        "questionSelector": selector,
        "debug": {
            "questionKey": question_key,
            "stageKey": stage_key,
            "recommendedAction": timing_contact.get("recommendedAction"),
            "topBand": timing_window.get("topBand"),
            "dominantSignals": dominant_signals,
            "repeatedThemeKey": (relationship_theme or {}).get("themeKey") if isinstance(relationship_theme, dict) else None,
        },
    }


def timing_guidance_payload(
    *,
    timing_contact: dict[str, Any],
    timing_window: dict[str, Any],
    timing_selectors: dict[str, dict[str, Any]],
    question_key: str,
    stage_key: str,
    relationship_theme: dict[str, Any] | None = None,
    source_claim_ids: list[str] | None = None,
    question_selector: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selector = selector_trace_payload(question_selector, question_key=question_key)
    readable = timing_guidance_readable_interpretation(
        timing_contact=timing_contact,
        timing_window=timing_window,
        timing_selectors=timing_selectors,
        question_key=question_key,
        stage_key=stage_key,
        relationship_theme=relationship_theme,
        source_claim_ids=source_claim_ids,
        question_selector=selector,
    )
    signals = timing_guidance_signals(timing_contact=timing_contact, timing_selectors=timing_selectors)
    return {
        "version": "timing-guidance-v1",
        "recommendedAction": timing_contact.get("recommendedAction"),
        "recommendedActionLabel": timing_contact.get("recommendedActionLabel"),
        "contactMode": timing_contact.get("contactMode"),
        "topBand": timing_window.get("topBand") or timing_contact.get("topBand"),
        "topBandLabel": timing_window.get("topBandLabel") or timing_contact.get("topBandLabel"),
        "sampleCount": timing_contact.get("sampleCount") or timing_window.get("sampleCount") or 0,
        "preciseDatesAvailable": False,
        "selectedSignals": signals,
        "nextMove": readable.get("nextMove"),
        "relationshipTheme": relationship_theme or {},
        "questionSelector": selector,
        "methodClaimIds": selector.get("methodClaimIds") or [],
        "evidenceClusterKeys": selector.get("evidenceClusterKeys") or [],
        "readableInterpretation": readable,
    }


def question_answer_readable_payload(
    *,
    question_key: str,
    question_label: str,
    stage_key: str,
    thoughts: list[str],
    reasons: list[dict[str, Any]],
    chance: dict[str, Any],
    timeline: list[dict[str, Any]],
    donts: list[str],
    source_claim_ids: list[str] | None = None,
    contact_policy: dict[str, Any] | None = None,
    timing_guidance: dict[str, Any] | None = None,
    answer_guidance: dict[str, Any] | None = None,
    relationship_theme: dict[str, Any] | None = None,
    question_selector: dict[str, Any] | None = None,
) -> ReadableQuestionAnswer:
    claim_ids = source_claim_ids or []
    selector = selector_trace_payload(question_selector, question_key=question_key)
    action_policy = contact_policy or {}
    action_readable = contact_action_readable_interpretation(
        contact_policy=action_policy,
        question_key=question_key,
        stage_key=stage_key,
        relationship_theme=relationship_theme,
        source_claim_ids=claim_ids,
        question_selector=selector,
    )
    return {
        "version": "readable-question-answer-v1",
        "locale": "zh-TW",
        "questionKey": question_key,
        "questionLabel": question_label,
        "questionSelector": selector,
        "methodClaimIds": selector.get("methodClaimIds") or [],
        "evidenceClusterKeys": selector.get("evidenceClusterKeys") or [],
        "sections": {
            "answer": answer_guidance or {},
            "action": {
                "statusKey": action_policy.get("statusKey"),
                "statusLabel": action_policy.get("statusLabel"),
                "actionScale": action_policy.get("actionScale"),
                "actionMode": action_policy.get("actionMode"),
                "blockedActions": action_policy.get("blockedActions") or [],
                "nextMove": action_readable.get("nextMove"),
                "relationshipTheme": relationship_theme or {},
                "questionSelector": selector,
                "methodClaimIds": selector.get("methodClaimIds") or [],
                "evidenceClusterKeys": selector.get("evidenceClusterKeys") or [],
                "readableInterpretation": action_readable,
            },
            "timing": timing_guidance or {},
            "thoughts": [
                {
                    "body": normalize_zh_text(item),
                    "readableInterpretation": thought_readable_interpretation(
                        body=item,
                        index=index,
                        question_key=question_key,
                        stage_key=stage_key,
                        source_claim_ids=claim_ids,
                        question_selector=selector,
                    ),
                    "questionSelector": selector,
                    "methodClaimIds": selector.get("methodClaimIds") or [],
                    "evidenceClusterKeys": selector.get("evidenceClusterKeys") or [],
                }
                for index, item in enumerate(thoughts, start=1)
            ],
            "reasons": reasons,
            "chance": chance,
            "timeline": timeline,
            "donts": [
                {
                    "body": normalize_zh_text(item),
                    **repeated_theme_compact_metadata(relationship_theme),
                    "questionSelector": selector,
                    "methodClaimIds": unique_strings([
                        *list((repeated_theme_compact_metadata(relationship_theme).get("methodClaimIds") or [])),
                        *list(selector.get("methodClaimIds") or []),
                    ]),
                    "evidenceClusterKeys": selector.get("evidenceClusterKeys") or [],
                    "readableInterpretation": boundary_readable_interpretation(
                        body=item,
                        index=index,
                        question_key=question_key,
                        stage_key=stage_key,
                        source_claim_ids=claim_ids,
                        question_selector=selector,
                    ),
                }
                for index, item in enumerate(donts, start=1)
            ],
        },
    }


FINAL_READING_SECTION_IDS = (
    "chart-positioning",
    "relationship-fit",
    "core-answer",
    "timing-reading",
    "action-direction",
)


def first_dict_item(values: Any) -> dict[str, Any]:
    for item in values or []:
        if isinstance(item, dict):
            return item
    return {}


def collect_dict_values(key: str, *values: Any) -> list[str]:
    collected: list[Any] = []
    for value in values:
        if isinstance(value, dict):
            collected.extend(value.get(key) or [])
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    collected.extend(item.get(key) or [])
    return unique_strings(collected)


def profile_card(person: dict[str, Any], point: str) -> dict[str, Any]:
    for card in person.get("cards") or []:
        if isinstance(card, dict) and str(card.get("point") or "") == point:
            return card
    return {}


def translation_baseline(relationship_profiles: dict[str, Any], person_key: str) -> dict[str, Any]:
    baseline = relationship_profiles.get("translationBaseline") if isinstance(relationship_profiles.get("translationBaseline"), dict) else {}
    if isinstance(baseline.get(person_key), dict):
        return baseline.get(person_key) or {}
    person = relationship_profiles.get(person_key) if isinstance(relationship_profiles.get(person_key), dict) else {}
    nested = person.get("translationBaseline") if isinstance(person.get("translationBaseline"), dict) else {}
    return nested or {}


def baseline_field(baseline: dict[str, Any], field: str, fallback: Any) -> str:
    return sanitize_public_answer_text(baseline.get(field) or fallback)


def aspect_everyday_signal(item: dict[str, Any], block: dict[str, Any], fallback: str) -> str:
    return sanitize_public_answer_text(
        item.get("everydaySignal")
        or item.get("meaning")
        or item.get("body")
        or block.get("summary")
        or fallback
    )


RELATIONSHIP_FIT_ATTRACTION_BANK: dict[str, tuple[str, ...]] = {
    "": (
        "你們確實容易被彼此牽動，但這只能說明還有火花，不能代表關係已經有結果",
        "吸引點在於對方會讓你想確認、想靠近，也會讓互動很快變得有感",
        "你們不是完全無感的組合，真正要看的是這份牽動能不能落到穩定互動",
        "靠近感容易被啟動，但它需要有後續行動接住，才不會只停在想像裡",
        "這段關係的吸引比較像被對方帶動情緒和注意力，而不是單純理性判斷",
        "有些反應會讓你覺得對方還在牽動你，也讓你很難把這段關係當成普通關係",
    ),
    "Venus-Mars": (
        "一方的好感會碰到另一方的行動感，所以很容易有想靠近、想確認反應的火花",
        "你們的吸引不是安靜型，而是會讓人想試探、想互動、想知道對方下一步怎麼接",
        "這種火花會把身體感和好奇心一起帶出來，靠近感通常來得比較快",
    ),
    "Sun-Moon": (
        "一方的存在感會碰到另一方的情緒節奏，所以容易有熟悉、被理解或被牽動的感覺",
        "你們比較容易在日常反應裡感覺到對方，不一定熱烈，但會有被放在心上的感覺",
        "吸引點在於一個人的自然表現，會讓另一個人的情緒比較有回應",
    ),
    "Moon-Moon": (
        "兩個人的情緒節奏容易互相感應，舒服時很貼近，不安時也容易一起被帶動",
        "你們對氣氛和情緒變化都比較敏感，所以一個人鬆了，另一個人也比較容易跟著鬆",
        "吸引點在於情緒頻率有接到的地方，像是不用講太多也會被對方影響",
    ),
    "Moon-Venus": (
        "情緒需求和被珍惜的感覺容易接上，被對方溫柔對待時會特別有感",
        "你們的好感比較容易從照顧、在意和被善待的細節裡慢慢被打開",
        "這個吸引點不是只有熱度，而是某些溫柔反應會讓人覺得被接住",
    ),
    "Sun-Venus": (
        "被看見、被欣賞的感覺容易被啟動，所以好感會先從在意和吸引開始",
        "你們容易在欣賞、外在吸引或被肯定的感覺裡拉近距離",
        "吸引點在於對方讓人覺得自己有被喜歡、被注意，關係因此比較容易升溫",
    ),
    "Sun-Mars": (
        "一方的存在感會激起另一方想靠近或採取行動的衝動，火花來得快，也容易急著測反應",
        "你們的吸引帶有推進感，喜歡的感覺一出現，就容易想立刻做點什麼",
        "這種火花比較像被對方點燃行動慾，靠近時很有感，但也容易快過頭",
    ),
    "Venus-Venus": (
        "喜歡的方式比較容易互相理解，舒服的陪伴和美感共鳴會拉近距離",
        "你們容易在相似的喜好、相處品味或被珍惜的方式裡覺得對方順眼",
        "吸引點偏向舒服和認同感，會讓關係有一種比較自然的靠近理由",
    ),
}

RELATIONSHIP_FIT_FRICTION_BANK: dict[str, tuple[str, ...]] = {
    "": (
        "卡住的地方不是單一事件，而是靠近之後節奏、安全感和說法容易接不上",
        "一旦互動變重要，兩個人就容易各自用保護自己的方式回應，讓話題變重",
        "真正摩擦點在於你們都被牽動，但處理不安和壓力的方法不一樣",
        "關係一進到需要回應的位置，就容易有人變急、有人變慢，於是誤會被放大",
        "你們不是沒有連結，而是連結一變緊，就容易把在乎表現成防衛或催促",
        "兩個人都在保護自己，所以同一句話很容易被聽成壓力",
    ),
    "Mercury-Mars": (
        "一想把話說清楚，就容易變成辯論、反駁或語氣太快",
        "真正卡住的常常不是沒話說，而是話一急，就像在互相修正或反擊",
        "溝通裡很容易出現速度差：一方想快點講完，另一方只感覺被推著回答",
    ),
    "Mars-Mars": (
        "兩個人一急一慢時，很容易變成誰都覺得對方不配合",
        "你們卡住時比較像步調互撞，一方想前進，另一方覺得被催",
        "衝突點在行動節奏，不一定是誰不在乎，而是做法和速度很容易互相頂到",
    ),
    "Moon-Mars": (
        "情緒被點到時，反應會很快，容易從在乎變成刺激",
        "一方只是情緒被碰到，另一方卻可能感覺被攻擊，氣氛會很快升高",
        "你們容易在情緒和行動之間互相觸發，越在乎越容易反應過快",
    ),
    "Mercury-Saturn": (
        "一想把話講清楚，就容易碰到標準、責任或被糾正的壓力，對話會變慢",
        "溝通卡點在於話題一正式，對方可能先進入審慎、防守或挑細節的狀態",
        "你想要理解，對方卻可能聽成要交代，於是話越講越重",
    ),
    "Moon-Saturn": (
        "情緒需要被接住時，另一方可能先冷靜、保留或拉開距離，讓安撫變難",
        "卡住的地方是需要安撫的時候，對方反而用理性、沉默或距離處理",
        "你要的是情緒被抱住，對方給的可能是規則或界線，落差會讓人更不安",
    ),
    "Venus-Saturn": (
        "想確認被珍惜時，容易碰到現實限制、承諾壓力或對方保留，甜的感覺會變重",
        "好感不是沒有，但一談到穩定、名分或付出，氣氛就容易變得謹慎",
        "你們的甜會碰到現實檢查：喜歡之外，還要看對方願不願意穩定付出",
    ),
    "Mars-Saturn": (
        "一方想推進，另一方像踩剎車；速度差會讓行動卡住，甚至像被擋下來",
        "卡住的地方在行動阻力：越想快點處理，越容易感覺對方不配合",
        "你們容易出現一個催、一個收的節奏，最後雙方都覺得自己被對方限制",
    ),
    "Sun-Saturn": (
        "想被肯定或自然做自己時，容易碰到標準、責任或被審核的感覺，靠近會變拘謹",
        "關係一變正式，就容易有誰被要求成熟、負責或表現得更好的壓力",
        "卡住點在自我表達被壓住：越想自然相處，越容易被現實標準拉回來",
    ),
}

RELATIONSHIP_FIT_GROWTH_BANK: dict[str, tuple[str, ...]] = {
    "": (
        "修復點在於把互動變得更小、更清楚，讓對方不用一次承接整段關係",
        "真正有用的是讓下一步可回答、可停下來，也不把結果壓在同一次互動",
        "這段關係需要把感覺翻成可做到的小行動，才不會又回到猜測和防衛",
        "比較能往前的方式，是先讓一次互動變穩，再看下一次會不會自然延續",
        "成長點不是講更多，而是把對方能接住的部分先留下來",
    ),
    "Mercury-Jupiter": (
        "修復點在於把話說開但不誇大；用更大的視角談一件具體小事",
        "你們比較適合把對話從對錯拉回理解，但一次只處理一個可回答的問題",
        "有用的是讓彼此看見更大的脈絡，同時不要把承諾說得比現實更多",
    ),
    "Sun-Saturn": (
        "修復點在於把欣賞落成可做到的支持，不用一次要求完整承諾",
        "這段關係要靠穩定的小行動恢復信任，不適合只靠一句表態撐住",
        "真正有用的是讓肯定變得可執行，讓對方知道怎麼靠近才不會被審核",
    ),
    "Moon-Saturn": (
        "修復點在於穩定安撫和固定回應，讓情緒不用每次都重新猜",
        "你們需要的是可預期的安撫，不是每次不安都重新談一次關係",
        "有用的是建立小而固定的安全感，例如回應節奏、界線和可做到的承諾",
    ),
    "Venus-Saturn": (
        "修復點在於小而穩定的在意感；說到做到，比一次大表態更有用",
        "喜歡要落到可被看見的付出，否則甜的感覺很容易又被現實壓回去",
        "這段關係需要穩定地證明在意，而不是靠一次熱絡重新定義全部",
    ),
    "Mars-Saturn": (
        "修復點在於先約好節奏，讓行動不再一個催、一個退",
        "有用的是把下一步變小、變清楚，讓對方知道不用立刻被推到終點",
        "你們需要先把靠近的份量收小，不然修復很容易又變成一個催、一個退",
    ),
}

RELATIONSHIP_FIT_REPAIR_BY_PAIR: dict[tuple[str, str], tuple[str, ...]] = {
    ("saturn_pressure", "attraction_pursuit"): (
        "先讓好感留在輕鬆互動裡，不要一有火花就檢查承諾",
        "把靠近做小一點，讓對方先感覺不需要立刻負責",
    ),
    ("action_conflict", "attraction_pursuit"): (
        "把想測反應的衝動收小，先做一個不需要對方表態的小動作",
        "有火花可以先放著，下一步只做短而輕的一件事，不逼出答案",
    ),
    ("action_conflict", "emotional_safety"): (
        "先說一個具體感受，不要求對方一次給完整安全感",
        "把不安翻成可回答的小句子，避免用追問換安心",
    ),
    ("emotional_safety", "attraction_pursuit"): (
        "不要用火花逼出保證，先看對方在沒有被追問時會不會接住",
        "吸引可以留著，但安全感要靠穩定回應慢慢累積",
    ),
    ("attraction_pursuit", "action_conflict"): (
        "不要只看有沒有曖昧，要看能不能變成壓力小、能接下去的小互動，讓對方有空間自然接續",
        "有反應時更要降速，讓靠近不要變成對方必須立刻回答",
    ),
    ("identity_rhythm", "emotional_safety"): (
        "保留彼此台階，用不比較、不審判的語氣讓對方有空間靠近",
        "先把尊重感放回對話，不用逼對方承認才算有答案",
    ),
    ("communication_repair", "saturn_pressure"): (
        "一次只留一件事、一個語氣、一個對方可以晚點回的小回應",
        "把長篇解釋拆小，讓溝通不像關係審判",
    ),
    ("communication_repair", "action_conflict"): (
        "把語氣從追答案改成交代一件具體小事，說完就停",
        "修復不是多補一段，而是讓訊息短到不會推著對方回答",
    ),
    ("emotional_safety", "saturn_pressure"): (
        "用可觀察的小回應累積安全感，不用一次要完整答案",
        "先讓壓力變輕，再看對方能不能穩定承接一點點",
    ),
    ("action_conflict", "communication_repair"): (
        "先選一件最具體、壓力最小的事說，不把過去全部放進同一段訊息",
        "可以談，但要讓對話有停下來的位置，不要越講越像辯輸贏",
    ),
    ("outer_intensity", "saturn_pressure"): (
        "回到清楚、連續、被允許的回應，不靠回憶或巧合補答案",
        "感覺越重，越要尊重界線，回頭看對方有沒有清楚行動",
    ),
}

RELATIONSHIP_FIT_REPAIR_BY_DYNAMIC: dict[str, tuple[str, ...]] = {
    "saturn_pressure": (
        "把關係題目拆成小而可做到的行動，先降低責任壓力",
        "先看對方能不能接住具體安排，先不談完整定位",
        "讓壓力下降比逼出答案重要，承諾要從小行動開始看",
    ),
    "emotional_safety": (
        "先讓互動回到穩定和可預期，不用每次都重新確認關係",
        "把安全感需求說小一點，讓對方知道可以怎麼接住",
        "先看穩定回應，而不是用一次表態決定全部",
    ),
    "communication_repair": (
        "一次只處理一件具體小事，說清楚後就停",
        "把訊息變短、變清楚，讓對方有空間自然回應",
        "修復靠降低承接量，不靠把所有心情一次說完",
    ),
    "attraction_pursuit": (
        "讓火花先回到自然互動，不把一時熱絡直接當成進展",
        "看吸引之後有沒有連續行動，而不是只看當下有沒有曖昧",
        "把靠近放在低壓情境裡，讓好感有機會自然延續",
    ),
    "action_conflict": (
        "先把動作縮小，避免越想靠近，氣氛越緊",
        "把下一步改成能停下來的小互動，不用一次解決整段關係",
        "先讓對話不升溫，再談要不要往下一步走",
    ),
    "identity_rhythm": (
        "先保留彼此面子和台階，讓靠近不需要分輸贏",
        "把被看見的需求說得柔一點，不用逼對方立刻承認",
        "修復要從尊重感開始，讓對方不用防著被審判",
    ),
    "outer_intensity": (
        "把強烈感覺放回現實行動檢查，不用想像補空白",
        "先看有沒有清楚、連續、被允許的回應，再談下一步",
        "感覺再強，也要回到界線和具體行動，不用靠命定感推進",
    ),
}

RELATIONSHIP_FIT_VIABILITY_BY_QUESTION: dict[str, tuple[str, ...]] = {
    "still-love-me": (
        "不是猜他心裡有沒有感覺，而是看他會不會在沒有被追問時自然延續",
        "如果還有感覺，它需要變成穩定接話、主動靠近或具體行動",
        "答案要放在連續反應裡看，不用只盯著某一句話有沒有安撫你",
    ),
    "any-chance": (
        "機會不在一次訊息，而在舊循環有沒有變小、新回應能不能連續",
        "要看靠近之後是不是更穩，而不是只看還有沒有一瞬間的火花",
        "真正的機會會表現在可延續的互動，不只是一時熱絡",
    ),
    "when-to-contact": (
        "現在能不能承受一則短、輕、沒有追問的訊息，比哪一天更重要",
        "要先看語氣和聯絡方式能不能被接住，不適合一開口就問關係結果",
        "如果要開口，訊息大小要服從現在的壓力，而不是服從你的焦急",
    ),
    "what-did-i-do-wrong": (
        "重點不是把錯全部攬回自己，而是看哪個互動環節可以調小",
        "可以調整的是表達方式和行動節奏，不是把整段關係都判成你的錯",
        "先找出可改的一小段互動，比反覆追究誰錯更有用",
    ),
    "stay-or-let-go": (
        "要看這段互動有沒有讓你更穩，而不是只看你還有多捨不得",
        "值得繼續觀察的前提，是現實回應開始減少消耗、增加穩定",
        "如果等待只讓你更焦慮，就要先把重心收回來，不把自己放在耗損裡",
    ),
}

RELATIONSHIP_FIT_OBSERVABLE_BY_CONTACT: dict[str, tuple[str, ...]] = {
    "blocked": (
        "是否仍有被允許、尊重界線的既有通道，而不是繞路逼近",
        "對方有沒有重新開放正常通道，而不是只讓你靠猜測或繞路維持",
        "界線是否被尊重後，互動才有一點自然恢復的空間",
    ),
    "no-contact": (
        "是否出現不需要你連續推動的自然小通道",
        "有沒有一個不用你加碼、對方也願意接住的小回應",
        "沉默之後是否出現自然、低壓、能停下來的互動開口",
    ),
    "occasional-contact": (
        "偶爾回覆之後，對方會不會主動把話題多接一點",
        "回覆是不是只停在禮貌，還是開始有一點自然延續",
        "低壓訊息送出後，對方的語氣和長度有沒有變得比較穩",
    ),
    "still-in-contact": (
        "聊天是否由他主動延續，而不是每次都只回你丟出的題目",
        "既有對話裡，他會不會自己補充、提問或把互動往前帶",
        "你們還能聊的時候，重點是主動性和延續性有沒有回來",
    ),
    "living-or-working-together": (
        "共同場域裡是否能維持禮貌、自然、不逼談關係",
        "日常相遇能不能不尷尬、不把關係題一次攤開，先讓承受度回來",
        "同一個空間裡是否能先恢復正常互動，而不是每次都變成壓力",
    ),
}

RELATIONSHIP_FIT_BOUNDARY_BY_CONTACT: dict[str, tuple[str, ...]] = {
    "blocked": (
        "通道沒有恢復前，不要把在意或吸引當成可以越界的理由",
        "如果只能換帳號或請朋友代為聯絡，現在就不適合再靠近",
    ),
    "no-contact": (
        "沒有自然通道時，不要連續加碼，也不要用長文製造回應壓力",
        "沉默期先看對方會不會自然出現，不要一主動就逼對方給答案",
    ),
    "occasional-contact": (
        "偶爾回覆不能直接當成關係已經變穩，要看後面是否連續",
        "不要把一兩次回應放大成關係保證，先看節奏會不會自己延續",
    ),
    "still-in-contact": (
        "還能聊天不等於問題解決，真正要看他是否也願意主動延續",
        "不要因為還有對話就一次談完整段關係，先看互動能不能變穩",
    ),
    "living-or-working-together": (
        "共同場域不是關係審問現場，先保護日常承受度",
        "如果相遇本身已經很緊，就不要再把場域變成關係壓力",
    ),
}

RELATIONSHIP_FIT_ARCHETYPE_MODIFIERS_BY_DYNAMIC: dict[str, tuple[str, ...]] = {
    "emotional_safety": ("情緒安全版", "安撫需求版", "敏感靠近版", "安全感回應版"),
    "saturn_pressure": ("責任壓力版", "慢熱承擔版", "現實檢查版", "承諾壓力版"),
    "communication_repair": ("溝通修復版", "短訊息修復版", "說法調整版", "對話降壓版"),
    "attraction_pursuit": ("火花追逐版", "吸引降速版", "熱度觀察版", "靠近測試版"),
    "action_conflict": ("推進摩擦版", "速度差版", "行動降溫版", "急慢失衡版"),
    "identity_rhythm": ("自尊節奏版", "台階修復版", "被看見需求版", "尊重感修復版"),
    "outer_intensity": ("強烈牽動版", "界線確認版", "命定感降溫版", "現實驗證版"),
}

RELATIONSHIP_FIT_ATTRACTION_CONTEXT_BY_QUESTION: dict[str, tuple[str, ...]] = {
    "still-love-me": (
        "這題要看它會不會變成主動留下，而不是只看一時有沒有熱度",
        "它比較像還有牽動的證據，但需要被後續回應驗證",
    ),
    "any-chance": (
        "真正加分的是火花後還願不願意接續，不是只有當下曖昧",
        "機會要看吸引之後能不能變成穩定靠近",
    ),
    "when-to-contact": (
        "如果真的要開口，也只適合短短一句，不要把情緒全放進去",
        "你想靠近是可以理解的，但訊息要短一點、輕一點",
    ),
    "what-did-i-do-wrong": (
        "它提醒你們確實有牽動，不代表每次反應都是你的錯",
        "先把吸引和自責分開看，才不會把所有波動都攬回自己身上",
    ),
    "stay-or-let-go": (
        "它說明為什麼難放下，但不能單獨當作繼續理由",
        "要看這份牽動讓你更穩，還是只讓你反覆等待",
    ),
}

RELATIONSHIP_FIT_FRICTION_CONTEXT_BY_STAGE: dict[str, tuple[str, ...]] = {
    "ambiguous": (
        "曖昧不明時，每個回覆都容易被過度解讀",
        "沒有說清楚的狀態，會讓一點小反應都變得很重",
    ),
    "broke-up-recent": (
        "分開不久時，很容易被放大成是不是不愛了",
        "剛分開的情緒會讓小摩擦看起來像最後答案",
    ),
    "cold-war": (
        "冷戰時會表現成誰先開口都怕輸",
        "沉默會把原本的小摩擦拖成面子和安全感問題",
    ),
    "broke-up-long": (
        "拖久後會變成一靠近就先想到舊問題",
        "時間拉長後，對方可能先防舊循環，而不是先回應你",
    ),
    "crisis": (
        "危機期會讓小語氣也像關係表態",
        "壓力高的時候，任何推進都容易被聽成逼答案",
    ),
}

RELATIONSHIP_FIT_VIABILITY_CONTEXT_BY_CONTACT: dict[str, tuple[str, ...]] = {
    "blocked": (
        "前提是正常通道先被尊重地恢復",
        "不能靠繞路證明關係還有機會",
    ),
    "no-contact": (
        "前提是沉默裡出現一次很輕、能自然停下的回應",
        "第一次主動不要變成逼對方給答案",
    ),
    "occasional-contact": (
        "關鍵是對方是否開始多接一點，而不是只禮貌回覆",
        "要看偶爾回覆能不能變成比較連續的互動",
    ),
    "still-in-contact": (
        "要看聊天裡是否也有對方主動補充，而不是只維持表面聯絡",
        "如果每天聊卻沒有變穩，仍然不能算真正往前",
    ),
    "living-or-working-together": (
        "要先保住共同場域的承受度，再看關係能不能談",
        "日常相遇如果先變穩，後面才有空間談更深",
    ),
}

RELATIONSHIP_FIT_REPAIR_CONTEXT_BY_CONTACT: dict[str, tuple[str, ...]] = {
    "blocked": (
        "通道未恢復前先不繞路",
        "先尊重界線，不把修復變成追逼",
    ),
    "no-contact": (
        "留一個對方可以不回也不尷尬的位置",
        "訊息要有停點，不要連續加碼",
    ),
    "occasional-contact": (
        "讓對方有機會自然多接一句",
        "先接住偶爾回覆，先不把話題推到關係",
    ),
    "still-in-contact": (
        "不要把每天聊天變成每天審問",
        "先讓日常對話恢復舒服，再談關係問題",
    ),
    "living-or-working-together": (
        "先保住共同場域的正常感",
        "不要讓相遇本身變成關係審問壓力",
    ),
}

RELATIONSHIP_FIT_OBSERVABLE_CONTEXT_BY_DYNAMIC: dict[str, tuple[str, ...]] = {
    "emotional_safety": ("看對方是否能穩定接住情緒，而不是只偶爾溫柔",),
    "saturn_pressure": ("看對方是否願意用小行動承擔，而不是只口頭安撫",),
    "communication_repair": ("看對方是否願意把話接清楚，而不是只避開衝突",),
    "attraction_pursuit": ("看熱度後面有沒有連續行動，而不是只有曖昧感",),
    "action_conflict": ("看你們能不能越聊越平，而不是誰先把局面扳回來",),
    "identity_rhythm": ("看彼此是否能保留台階，而不是逼誰先認輸",),
    "outer_intensity": ("看現實行動是否連續清楚，而不是靠感覺補空白",),
}

RELATIONSHIP_FIT_BOUNDARY_CONTEXT_BY_QUESTION: dict[str, tuple[str, ...]] = {
    "still-love-me": ("不要把想確認愛不愛，變成對方必須立刻證明",),
    "any-chance": ("不要把一次有反應，直接當成復合窗口",),
    "when-to-contact": ("不要用訊息測答案，只做對方能承受的一步",),
    "what-did-i-do-wrong": ("不要把所有沉默都解讀成你做錯了",),
    "stay-or-let-go": ("不要為了等一個可能性，把自己放進持續耗損",),
}


def deterministic_variant(values: tuple[str, ...], *keys: Any) -> str:
    choices = tuple(sanitize_public_answer_text(value) for value in values if sanitize_public_answer_text(value))
    if not choices:
        return ""
    seed = "|".join(str(key or "") for key in keys)
    total = sum((index + 1) * ord(char) for index, char in enumerate(seed))
    return choices[total % len(choices)]


def bank_phrase(bank: dict[Any, tuple[str, ...]], key: Any, fallback: str, *selectors: Any) -> str:
    selected = deterministic_variant(bank.get(key, ()) or bank.get("", ()), key, *selectors)
    return selected or sanitize_public_answer_text(fallback)


def relationship_fit_pair_key(item: dict[str, Any]) -> str:
    return sanitize_public_answer_text(item.get("pairKey") or "")


def relationship_fit_append_clause(text: str, clause: str, max_chars: int = 150) -> str:
    base = sanitize_public_answer_text(text)
    extra = sanitize_public_answer_text(clause)
    if not base or not extra or extra in base:
        return base
    candidate = f"{base}；{extra}"
    normalized = re.sub(r"\s+", "", candidate)
    semicolon_count = normalized.count("；") + normalized.count(";")
    if len(normalized) <= max_chars and semicolon_count <= 2:
        return candidate
    return base


def relationship_fit_redundant_repair(base: str, detail: str) -> bool:
    normalized_base = re.sub(r"\s+", "", sanitize_public_answer_text(base))
    normalized_detail = re.sub(r"\s+", "", sanitize_public_answer_text(detail))
    if not normalized_base or not normalized_detail:
        return False
    if normalized_base[:10] == normalized_detail[:10]:
        return True
    overlap_markers = (
        "不要用火花逼出保證",
        "把火花落到具體",
        "先選一件最具體",
        "不把過去全部放進同一段訊息",
        "不把整段關係壓在同一次對話",
        "小而可觀察的互動",
        "讓對方在沒有被追問時",
    )
    return any(marker in normalized_base and marker in normalized_detail for marker in overlap_markers)


def relationship_fit_archetype_label(
    *,
    archetype_title: str,
    primary_key: str,
    secondary_key: str,
    question_key: str,
    stage_key: str,
    contact_key: str,
) -> str:
    title = sanitize_public_answer_text(archetype_title or "需要磨合的關係型態")
    modifier = bank_phrase(
        RELATIONSHIP_FIT_ARCHETYPE_MODIFIERS_BY_DYNAMIC,
        primary_key or secondary_key,
        "",
        secondary_key,
    )
    return f"{title}・{modifier}" if modifier else title


def relationship_fit_repair_direction(
    *,
    primary_key: str,
    secondary_key: str,
    pair_repair: str,
    repair_summary: str,
    growth_signal: str,
    question_key: str,
    stage_key: str,
    contact_key: str,
) -> str:
    pair_variant = bank_phrase(
        RELATIONSHIP_FIT_REPAIR_BY_PAIR,
        (primary_key, secondary_key),
        "",
        primary_key,
        secondary_key,
    )
    dynamic_variant = bank_phrase(
        RELATIONSHIP_FIT_REPAIR_BY_DYNAMIC,
        primary_key or secondary_key,
        "",
        secondary_key,
    )
    base = sanitize_public_answer_text(pair_repair or repair_summary or dynamic_variant or growth_signal)
    detail = sanitize_public_answer_text(pair_variant or dynamic_variant)
    if base and detail and detail not in base:
        if base.startswith("修復要") or relationship_fit_redundant_repair(base, detail):
            return detail
        candidate = relationship_fit_append_clause(detail, base, max_chars=165)
        return candidate or detail
    return base or detail or growth_signal


def build_relationship_fit_narrative(
    *,
    archetype_title: str,
    question_key: str,
    stage_key: str,
    contact_key: str,
    primary_key: str,
    secondary_key: str,
    attraction_item: dict[str, Any],
    conflict_item: dict[str, Any],
    growth_item: dict[str, Any],
    attraction_signal: str,
    conflict_signal: str,
    growth_signal: str,
    tension_shift: str,
    pair_dynamic_interaction: str,
    pair_repair: str,
    repair_summary: str,
    sign_behaviors: list[str],
) -> dict[str, str]:
    attraction_pair = relationship_fit_pair_key(attraction_item)
    conflict_pair = relationship_fit_pair_key(conflict_item)
    growth_pair = relationship_fit_pair_key(growth_item)
    attraction_text = bank_phrase(
        RELATIONSHIP_FIT_ATTRACTION_BANK,
        attraction_pair,
        attraction_signal,
        primary_key,
        secondary_key,
    )
    friction_text = bank_phrase(
        RELATIONSHIP_FIT_FRICTION_BANK,
        conflict_pair,
        conflict_signal,
        primary_key,
        secondary_key,
    )
    growth_text = bank_phrase(
        RELATIONSHIP_FIT_GROWTH_BANK,
        growth_pair,
        growth_signal,
        primary_key,
        secondary_key,
    )
    viability = sanitize_public_answer_text(tension_shift or growth_text)
    repair_direction = relationship_fit_repair_direction(
        primary_key=primary_key,
        secondary_key=secondary_key,
        pair_repair=pair_repair,
        repair_summary=repair_summary,
        growth_signal=growth_text,
        question_key=question_key,
        stage_key=stage_key,
        contact_key=contact_key,
    )
    observable = bank_phrase(
        RELATIONSHIP_FIT_GROWTH_BANK,
        growth_pair,
        sign_behaviors[0] if sign_behaviors else growth_text,
        primary_key,
        secondary_key,
    )
    boundary = bank_phrase(
        RELATIONSHIP_FIT_BOUNDARY_CONTEXT_BY_QUESTION,
        "",
        "",
        primary_key,
        secondary_key,
    )
    archetype_label = relationship_fit_archetype_label(
        archetype_title=archetype_title,
        primary_key=primary_key,
        secondary_key=secondary_key,
        question_key="",
        stage_key="",
        contact_key="",
    )
    body = join_zh_sentences(
        f"你們的相處比較像「{archetype_label}」",
        f"吸引力在這裡：{attraction_text}",
        f"卡住的地方在這裡：{friction_text}",
        f"能不能繼續，要看：{viability}",
        f"接下來現實裡要看：{observable}",
    )
    return {
        "body": body,
        "attraction_signal": attraction_text,
        "friction_signal": friction_text,
        "viability_condition": viability,
        "repair_direction": repair_direction,
        "observable_proof": observable,
        "boundary_or_caution": boundary,
    }


def question_core_focus(question_key: str) -> str:
    return {
        "still-love-me": "這題真正要看的不是一句「還愛不愛」，而是對方還有沒有自然延續、願不願意把互動留在生活裡。",
        "any-chance": "這題真正要看的不是有沒有一次復合機會，而是舊循環能不能停下來，新的回應能不能連續出現。",
        "when-to-contact": "這題真正要看的不是哪一天一定最好，而是現在的語氣、通道和時機能不能承受一則訊息。",
        "what-did-i-do-wrong": "這題真正要看的不是誰該被判錯，而是哪一段互動讓你們各自的保護方式被觸發。",
        "stay-or-let-go": "這題真正要看的不是你還有沒有感覺，而是這段互動有沒有讓你回到比較安定的自己。",
    }.get(question_key, "這題要把星盤、現實互動和當下狀態放在一起看，不能只抓單一反應下結論。")


def final_section_readable(
    *,
    module: str,
    headline: str,
    meaning: str,
    body: str,
    next_move: str,
    caution: str,
    selector: dict[str, Any],
    source_claim_ids: list[str],
    method_claim_ids: list[str],
    evidence_cluster_keys: list[str],
    case_model_trace: dict[str, Any] | None = None,
) -> ReadableInterpretation:
    def final_text(value: Any) -> str:
        # FinalNarrativeFactRenderer owns the final visible wording. Legacy
        # sanitizers remain available for upstream diagnostics, but applying
        # them here would make controlled copy unstable again.
        return normalize_zh_text(value)

    readable: ReadableInterpretation = {
        "version": "readable-interpretation-v1",
        "module": module,
        "locale": "zh-TW",
        "headline": final_text(headline),
        "meaning": final_text(meaning),
        "body": final_text(body),
        "nextMove": final_text(next_move),
        "caution": final_text(caution),
        "confidenceNote": "這是根據本次星盤與現實情境做出的條件式判讀。",
        "sourceClaimIds": unique_strings(source_claim_ids),
        "methodClaimIds": unique_strings(method_claim_ids or selector.get("methodClaimIds") or []),
        "evidenceClusterKeys": unique_strings(evidence_cluster_keys or selector.get("evidenceClusterKeys") or []),
        "questionSelector": selector,
    }
    if case_model_trace:
        readable["caseModelTrace"] = dict(case_model_trace)  # type: ignore[typeddict-item]
    return readable


def final_reading_interpretation_payload(
    *,
    question_key: str,
    question_label: str,
    stage_key: str,
    relationship_profiles: dict[str, Any],
    relationship_archetype: dict[str, Any],
    attraction_dynamics: dict[str, Any],
    conflict_dynamics: dict[str, Any],
    growth_dynamics: dict[str, Any],
    partner_needs: dict[str, Any],
    fight_landmines: dict[str, Any],
    survival_guide: dict[str, Any],
    relationship_turning_windows: dict[str, Any],
    answer_guidance: dict[str, Any],
    normal_user_answer: dict[str, Any],
    timing_guidance: dict[str, Any],
    action_guidance: dict[str, Any],
    contact_policy: dict[str, Any],
    relationship_theme: dict[str, Any] | None = None,
    relationship_thesis: dict[str, Any] | None = None,
    relationship_case_model: dict[str, Any] | None = None,
    dominant_narrative_angle: dict[str, Any] | None = None,
    context_storyline: dict[str, Any] | None = None,
    source_claim_ids: list[str] | None = None,
    question_selector: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selector = selector_trace_payload(question_selector, question_key=question_key)
    thesis = relationship_thesis or {}
    case_model = relationship_case_model or {}
    storyline = context_storyline or case_model.get("contextStoryline") or {}
    status_policy = storyline.get("statusAnswerPolicy") if isinstance(storyline.get("statusAnswerPolicy"), dict) else {}
    if not status_policy and isinstance(case_model.get("statusAnswerPolicy"), dict):
        status_policy = case_model.get("statusAnswerPolicy") or {}

    def storyline_value(key: str) -> str:
        return sanitize_public_answer_text(storyline.get(key) or "")

    primary_dynamic = case_model.get("primaryDynamic") if isinstance(case_model.get("primaryDynamic"), dict) else {}
    repair_lever = case_model.get("repairLever") if isinstance(case_model.get("repairLever"), dict) else {}
    contact_posture = case_model.get("contactPosture") if isinstance(case_model.get("contactPosture"), dict) else {}
    risk_posture = case_model.get("riskPosture") if isinstance(case_model.get("riskPosture"), dict) else {}
    answer_strategy = case_model.get("answerStrategy") if isinstance(case_model.get("answerStrategy"), dict) else {}
    dynamic_interaction_plan = case_model.get("dynamicInteractionPlan") if isinstance(case_model.get("dynamicInteractionPlan"), dict) else {}
    thesis_boundary = thesis.get("decisionBoundary") if isinstance(thesis.get("decisionBoundary"), dict) else {}
    thesis_signs = [item for item in thesis.get("observableSigns") or [] if isinstance(item, dict)]
    central_thesis = sanitize_public_answer_text(primary_dynamic.get("centralThesis") or thesis.get("centralThesis") or "")
    question_reframe = sanitize_public_answer_text(thesis.get("questionReframe") or "")
    repair_summary = sanitize_public_answer_text(repair_lever.get("summary") or "")
    risk_guidance = sanitize_public_answer_text(risk_posture.get("guidance") or "")
    pair_action_boundary = sanitize_public_answer_text(dynamic_interaction_plan.get("actionBoundary") or "")
    sign_behaviors = [
        sanitize_public_answer_text(item.get("behavior"))
        for item in thesis_signs[:3]
        if sanitize_public_answer_text(item.get("behavior"))
    ]
    sign_summary = "；".join(sign_behaviors) if sign_behaviors else "對方是否自然延續；語氣是否放鬆；行動是否比以前更穩"
    contact_key = storyline_value("contactKey") or str(contact_posture.get("statusKey") or contact_policy.get("statusKey") or "")
    section_specs = build_section_narrative_specs(
        question_key=question_key,
        stage_key=stage_key,
        contact_key=contact_key,
        relationship_profiles=relationship_profiles,
        relationship_archetype=relationship_archetype,
        attraction_dynamics=attraction_dynamics,
        conflict_dynamics=conflict_dynamics,
        growth_dynamics=growth_dynamics,
        relationship_thesis=thesis,
        relationship_case_model=case_model,
        status_answer_policy=status_policy,
        timing_guidance=timing_guidance,
        action_guidance=action_guidance,
        relationship_turning_windows=relationship_turning_windows,
        relationship_theme=relationship_theme,
    )
    final_semantic_input = FinalNarrativeSemanticInput(
        question_key=question_key,
        stage_key=stage_key,
        contact_key=contact_key,
        section_specs=section_specs,
        fact_contract=section_specs.get("finalNarrativeFacts"),
    )
    final_composer = FinalNarrativeComposer.from_semantic_input(final_semantic_input)
    final_drafts = final_composer.render_all()

    def section_trace(section_id: str, key: str) -> list[str]:
        section = (section_specs.get("sections") or {}).get(section_id) or {}
        trace = section.get("trace") if isinstance(section.get("trace"), dict) else {}
        return unique_strings(trace.get(key) or [])

    def section_case_model_trace(section_id: str) -> dict[str, Any]:
        section = (section_specs.get("sections") or {}).get(section_id) or {}
        trace = section.get("caseModelTrace") if isinstance(section.get("caseModelTrace"), dict) else {}
        return dict(trace)

    person_a = relationship_profiles.get("personA") or {}
    person_b = relationship_profiles.get("personB") or {}
    baseline_a = translation_baseline(relationship_profiles, "personA")
    baseline_b = translation_baseline(relationship_profiles, "personB")
    a_moon = profile_card(person_a, "Moon")
    a_mercury = profile_card(person_a, "Mercury")
    b_saturn = profile_card(person_b, "Saturn")
    you_emotional_need = baseline_field(
        baseline_a,
        "emotionalNeed",
        f"{sanitize_public_answer_text(a_moon.get('placement') or '你的月亮')}：你會用日常互動確認關係是否安定",
    )
    you_communication = baseline_field(
        baseline_a,
        "communicationStyle",
        f"{sanitize_public_answer_text(a_mercury.get('placement') or '你的水星')}：話說清楚，關係才比較容易回到可理解的位置",
    )
    partner_pressure = baseline_field(
        baseline_b,
        "conflictResponse",
        f"{sanitize_public_answer_text(b_saturn.get('placement') or '他的土星')}：緊張時反應可能會先收起來",
    )
    chart_draft = final_drafts["chart-positioning"]
    chart_section = final_section_readable(
        module="final_chart_positioning",
        headline=chart_draft.headline,
        meaning=chart_draft.meaning,
        body=chart_draft.body,
        next_move=chart_draft.next_move,
        caution=chart_draft.caution,
        selector=selector,
        source_claim_ids=section_trace("chart-positioning", "sourceClaimIds"),
        method_claim_ids=section_trace("chart-positioning", "methodClaimIds"),
        evidence_cluster_keys=section_trace("chart-positioning", "evidenceClusterKeys"),
    )

    attraction_item = first_dict_item(attraction_dynamics.get("items"))
    conflict_item = first_dict_item(conflict_dynamics.get("items"))
    growth_item = first_dict_item(growth_dynamics.get("items"))
    archetype_title = sanitize_public_answer_text(relationship_archetype.get("title") or "需要磨合的關係型態")
    attraction_signal = aspect_everyday_signal(attraction_item, attraction_dynamics, "互動裡容易出現想靠近、想被看見或想延續話題的反應")
    conflict_signal = aspect_everyday_signal(conflict_item, conflict_dynamics, "靠近之後容易因為語氣、速度或自尊感變得卡住")
    growth_signal = aspect_everyday_signal(growth_item, growth_dynamics, "比較有用的修復點，是找出一種兩個人都承受得住的新互動方式")

    def reader_signal(value: str, fallback: str) -> str:
        text = sanitize_public_answer_text(value)
        if "沒有足夠可展示" in text or "只保留方法邊界" in text:
            return fallback
        return text or fallback

    attraction_signal = reader_signal(attraction_signal, "你們之間仍有想靠近、也想知道對方反應的地方")
    conflict_signal = reader_signal(conflict_signal, "卡住的地方比較像互動節奏和安全感沒有接上")
    growth_signal = reader_signal(growth_signal, "真正有用的是讓互動變得更輕、更穩、能自然延續")
    fit_narrative = build_relationship_fit_narrative(
        archetype_title=archetype_title,
        question_key="",
        stage_key="",
        contact_key="",
        primary_key="",
        secondary_key="",
        attraction_item=attraction_item,
        conflict_item=conflict_item,
        growth_item=growth_item,
        attraction_signal=attraction_signal,
        conflict_signal=conflict_signal,
        growth_signal=growth_signal,
        tension_shift="",
        pair_dynamic_interaction="",
        pair_repair="",
        repair_summary="",
        sign_behaviors=[],
    )
    fit_draft = final_drafts["relationship-fit"]
    fit_section = final_section_readable(
        module="final_relationship_fit",
        headline=fit_draft.headline,
        meaning=fit_draft.meaning,
        body=fit_draft.body,
        next_move=fit_draft.next_move,
        caution=fit_draft.caution,
        selector=selector,
        source_claim_ids=section_trace("relationship-fit", "sourceClaimIds"),
        method_claim_ids=section_trace("relationship-fit", "methodClaimIds"),
        evidence_cluster_keys=section_trace("relationship-fit", "evidenceClusterKeys"),
    )

    partner_need = first_dict_item(partner_needs.get("items"))
    partner_profile = partner_needs.get("profile") if isinstance(partner_needs.get("profile"), dict) else {}
    answer_readable = answer_guidance.get("readableInterpretation") or {}
    direct_answer = sanitize_public_answer_text(answer_strategy.get("directAnswer") or normal_user_answer.get("directAnswer") or answer_guidance.get("shortAnswer") or answer_readable.get("body"))
    partner_relationship_need = sanitize_public_answer_text(
        partner_profile.get("relationshipStyleWanted")
        or partner_need.get("relationshipStyleWanted")
        or baseline_b.get("emotionalNeed")
        or partner_needs.get("framing")
        or "他需要用可觀察的反應來確認關係，而不是靠猜測補空白"
    )
    partner_relationship_need = partner_relationship_need.replace("從月亮看，他在親密關係裡最先尋找的是：", "")
    partner_opens = sanitize_public_answer_text(
        partner_profile.get("whatOpensHimUp")
        or partner_need.get("whatOpensHimUp")
        or baseline_b.get("closenessTrigger")
        or "穩定、清楚、不先把他的想法定死的互動"
    )
    partner_shuts = sanitize_public_answer_text(
        partner_profile.get("whatShutsHimDown")
        or partner_need.get("whatShutsHimDown")
        or baseline_b.get("withdrawalTrigger")
        or "被催促、被審問，或感覺沒有退路"
    )
    partner_misread = sanitize_public_answer_text(
        partner_profile.get("commonMisread")
        or partner_need.get("commonMisread")
        or baseline_b.get("misunderstandingRisk")
        or "退後或變慢不一定等於沒有感覺"
    )
    core_draft = final_drafts["core-answer"]
    core_section = final_section_readable(
        module="final_core_answer",
        headline=core_draft.headline,
        meaning=core_draft.meaning,
        body=core_draft.body,
        next_move=core_draft.next_move,
        caution=core_draft.caution,
        selector=selector,
        source_claim_ids=section_trace("core-answer", "sourceClaimIds"),
        method_claim_ids=section_trace("core-answer", "methodClaimIds"),
        evidence_cluster_keys=section_trace("core-answer", "evidenceClusterKeys"),
        case_model_trace=section_case_model_trace("core-answer"),
    )

    timing_readable = timing_guidance.get("readableInterpretation") or {}
    turning_item = first_dict_item(relationship_turning_windows.get("items"))
    timing_period_label = sanitize_public_answer_text(turning_item.get("periodLabel") or turning_item.get("windowLabel") or "")
    timing_window_title = sanitize_public_answer_text(turning_item.get("title") or relationship_turning_windows.get("saferLabel") or "關係重要轉折氣候")
    timing_action = str(timing_guidance.get("recommendedAction") or "")
    if timing_window_title == "承諾與責任壓力期":
        timing_window_title = {
            "avoid_push": "界線和承擔變敏感的時段",
            "low_pressure_message": "低壓靠近條件",
            "observe_for_soft_window": "先觀察柔和訊號",
            "observe_only": "目前節奏觀察",
            "not_calculated": "資料不足，保守判斷",
        }.get(timing_action, "界線和承擔變敏感的時段")
    timing_window_meaning = sanitize_public_answer_text(turning_item.get("meaning") or relationship_turning_windows.get("summary") or "它會提示哪種互動狀態比較需要留意")
    timing_headline = sanitize_public_answer_text(
        timing_readable.get("headline") or timing_guidance.get("recommendedActionLabel") or timing_window_title
    )
    timing_draft = final_drafts["timing-reading"]
    timing_section = final_section_readable(
        module="final_timing_reading",
        headline=timing_draft.headline,
        meaning=timing_draft.meaning,
        body=timing_draft.body,
        next_move=timing_draft.next_move,
        caution=timing_draft.caution,
        selector=selector,
        source_claim_ids=section_trace("timing-reading", "sourceClaimIds"),
        method_claim_ids=section_trace("timing-reading", "methodClaimIds"),
        evidence_cluster_keys=section_trace("timing-reading", "evidenceClusterKeys"),
        case_model_trace=section_case_model_trace("timing-reading"),
    )

    action_readable = action_guidance.get("readableInterpretation") or {}
    landmine_item = first_dict_item(fight_landmines.get("items"))
    survival_item = first_dict_item(survival_guide.get("items"))
    action_draft = final_drafts["action-direction"]
    action_section = final_section_readable(
        module="final_action_direction",
        headline=action_draft.headline,
        meaning=action_draft.meaning,
        body=action_draft.body,
        next_move=action_draft.next_move,
        caution=action_draft.caution,
        selector=selector,
        source_claim_ids=section_trace("action-direction", "sourceClaimIds"),
        method_claim_ids=section_trace("action-direction", "methodClaimIds"),
        evidence_cluster_keys=section_trace("action-direction", "evidenceClusterKeys"),
        case_model_trace=section_case_model_trace("action-direction"),
    )

    sections = {
        "chart-positioning": chart_section,
        "relationship-fit": fit_section,
        "core-answer": core_section,
        "timing-reading": timing_section,
        "action-direction": action_section,
    }
    final_case_model_trace = section_case_model_trace("core-answer")
    if final_case_model_trace:
        final_case_model_trace["sectionId"] = "final-reading"
    output = {
        "version": "final-reading-interpretation-v1",
        "locale": "zh-TW",
        "questionKey": question_key,
        "questionLabel": question_label,
        "stageKey": stage_key,
        "contextStoryline": storyline,
        "sections": sections,
        "sectionSpecs": section_specs,
        "sourceClaimIds": unique_strings([claim_id for section in sections.values() for claim_id in section.get("sourceClaimIds") or []]),
        "methodClaimIds": unique_strings([claim_id for section in sections.values() for claim_id in section.get("methodClaimIds") or []]),
        "evidenceClusterKeys": unique_strings([key for section in sections.values() for key in section.get("evidenceClusterKeys") or []]),
    }
    if final_case_model_trace:
        output["caseModelTrace"] = final_case_model_trace
    return output
