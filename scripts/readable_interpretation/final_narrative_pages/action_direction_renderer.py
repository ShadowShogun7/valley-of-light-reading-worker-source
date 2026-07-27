"""Reader-language realization for the one-action page."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Mapping

from ..final_narrative_chinese_contract import audit_native_zh_tw_text
from ..final_narrative_chinese_plan import ReaderMeaningFrame, frame_from_fact
from ..final_narrative_composition import normalize_copy
from ..final_narrative_paragraph_plan import (
    paragraph_plan,
    support_from_fact,
    validate_paragraph_output,
)
from ..final_narrative_fact_renderer import (
    ACTION_MODE_COPY,
    BLOCKED_ACTION_COPY,
    join_sentences,
)
from ..final_narrative_realization import RealizationForms, domain_index, select_context_variant
from ..final_narrative_semantic_coverage import (
    FinalNarrativeSemanticCoverageError,
    SectionFactReader,
    require_supported_value,
)
from ..final_narrative_semantic_domains import (
    CONTACT_STATUS_KEYS,
    QUESTION_KEYS,
    RELATIONSHIP_DYNAMIC_KEYS,
)


ACTION_DIRECTION_NATIVE_ZH_TW_CATALOG_VERSION = "action-direction-native-zh-tw-catalog-v5"


class ActionDirectionNativeChineseError(ValueError):
    """Raised when action copy is unsupported, untraceable, or too abstract."""


FORBIDDEN_ACTION_ABSTRACTIONS = (
    "副動力",
    "互動意願",
    "穩定投入",
    "通道未斷",
    "推進防衛",
    "修復線索",
    "關係線索",
    "低刺激",
    "可觀察條件",
    "行動要留在能確認的範圍",
)


QUESTION_HEADLINES = {
    "still-love-me": (
        "下一步先做不需要猜他心意的事",
        "下一步先看他有沒有主動靠近",
        "下一步用他的後續行動判斷心意",
        "下一步不要再靠猜測確認他的感情",
    ),
    "any-chance": (
        "下一步先確認修復是否真的可能",
        "下一步先看舊問題有沒有出現改變",
        "下一步用雙方行動確認還有沒有機會",
        "下一步先看這段關係能不能重新走穩",
    ),
    "when-to-contact": (
        "下一步先確認現在能不能開口",
        "下一步先看現在是否適合聯絡",
        "下一步先確認開口會不會增加壓力",
        "下一步用目前界線決定是否聯絡",
    ),
    "what-did-i-do-wrong": (
        "下一步只調整你真正能控制的事",
        "下一步先分清哪些事真的能調整",
        "下一步只改變你現在做得到的部分",
        "下一步不要把兩個人的問題全怪自己",
    ),
    "stay-or-let-go": (
        "下一步用實際反應保護自己的界線",
        "下一步用他的行動決定還要不要等",
        "下一步先看等待有沒有帶來新的回應",
        "下一步替自己設下繼續等待的界線",
    ),
}

CONTACT_POSTURE_TAGS = {
    "boundary-first": "目前先守住聯絡界線",
    "observe-channel": "先看聯絡是否自然恢復",
    "protect-shared-space": "共同場合只保留必要交流",
    "test-low-pressure": "只保留一次沒有要求的開口",
    "watch-initiation": "讓對方的主動性決定後續",
}

OBSERVABLE_RESPONSE_COPY = {
    "boundary-first": "只有他主動恢復原本的聯絡方式，才表示界線真的改變",
    "observe-channel": "你停止主動聯絡後，他仍會開口，才表示沉默開始鬆動",
    "protect-shared-space": "不談感情時仍能自然相處並維持禮貌，才算共同場合變得比較穩",
    "test-low-pressure": "簡短訊息告一段落後，他還會主動接著聊，才表示不只是禮貌回覆",
    "watch-initiation": "這次話題告一段落後，他還會主動開啟下一次對話，才表示不只你想維持聯絡",
}

OBSERVABLE_RESPONSE_VARIANTS = {
    "boundary-first": (
        OBSERVABLE_RESPONSE_COPY["boundary-first"],
        "他自己重開原本的聯絡方式，才算界線由他主動鬆動",
        "沒有繞過界線時，他仍主動恢復聯絡，才是值得注意的變化",
        "原本的聯絡方式由他主動打開，才表示目前界線真的不同了",
        "等他自己解除封鎖或恢復原本管道，才算聯絡許可重新出現",
        "他沒有受到提醒也主動重開聯絡，才表示不是你單方面突破界線",
        "原本關上的聯絡方式由他親自恢復，才值得重新判斷是否能互動",
        "只有他明確讓聯絡重新成立，才表示界線真的改變",
    ),
    "observe-channel": (
        OBSERVABLE_RESPONSE_COPY["observe-channel"],
        "你停下來後，他仍主動找你說話，才表示聯絡不只靠你維持",
        "不用你補訊息，他也會開啟下一次對話，才算互動開始恢復",
        "你沒有再加一步，他仍主動開口，才表示聯絡狀態真的不同",
        "這次沉默由他主動打破，才算聯絡開始恢復",
        "你先停下來後，他仍主動聯絡，才表示不是只有你在等待",
        "沒有新訊息提醒他，他仍主動開口，才是值得留意的改變",
        "你不再找理由聯絡後，他仍會開口，才表示沉默開始鬆動",
    ),
    "protect-shared-space": (
        OBSERVABLE_RESPONSE_COPY["protect-shared-space"],
        "不借共同場合談感情時，彼此仍能自然合作，才算日常壓力下降",
        "只保留必要往來後，共同場合不再緊繃，才表示相處開始恢復",
        "不談關係也能自然相處，而且彼此不再明顯防備，才算共同場合變穩",
        "沒有利用見面追問感情時，日常仍能放鬆，才表示共同空間安全一些",
        "工作或生活往來不再帶著明顯敵意，才算彼此能先恢復基本相處",
        "只談必要事情時，對方仍願意自然合作，才表示現場壓力正在下降",
        "共同場合能維持禮貌而不刻意閃避，才值得再觀察後續變化",
    ),
    "test-low-pressure": (
        OBSERVABLE_RESPONSE_COPY["test-low-pressure"],
        "一則簡短訊息後，他會自己接下一個話題，才表示互動不只是禮貌回應",
        "你沒有補第二段時，他仍願意把對話往下帶，才值得增加下一步",
        "簡短開口後他會自己接話，而不是只回一句，才表示這個做法有用",
        "一個日常話題結束後，他又主動問起別的事，才表示不只是禮貌回覆",
        "短訊息告一段落後，他還會主動接著聊，才值得保留下一次互動",
        "他不只回答原本問題，還願意主動多說一點，才表示對話有空間",
        "短訊息沒有帶來壓力，而且他之後仍會開口，才算互動真的放鬆",
    ),
    "watch-initiation": (
        OBSERVABLE_RESPONSE_COPY["watch-initiation"],
        "對話自然停下後，他仍會主動開新話題，才表示不只你想維持聯絡",
        "你不再追問後，他仍會主動接著聊，才表示他也想維持互動",
        "這次話題結束後，他仍會主動開啟下一次對話，才能說明他也想繼續聯絡",
        "誤會說清後他還會主動談別的事，才表示互動沒有只停在修正口氣",
        "你不再補充解釋時，他仍願意接著聊，才表示兩個人都在參與",
        "話題結束後，他仍會找機會開口，才表示不是由你一個人撐著",
        "他會主動回到日常對話，而不是只接受道歉，才值得考慮後續",
    ),
}

STOP_COPY = {
    "anxiety-guard": "如果你開始反覆查看訊息、改字或想補充，就先停止新的動作",
    "self-blame-guard": "如果你又把所有問題都怪在自己身上，就先停止補救和追問",
    "stability-first": "如果這次互動讓生活和情緒明顯失去平衡，就先暫停聯絡",
    "safety-first": "只要出現威脅、騷擾或人身安全疑慮，就停止接觸並尋求可信任的協助",
    "standard": "如果對方回得更短、口氣變硬或明確拒絕，就不要繼續靠近",
    "standard-boundary": "如果對方回得更短、口氣變硬或明確拒絕，就不要繼續靠近",
}

STOP_VARIANTS = {
    "anxiety-guard": (
        STOP_COPY["anxiety-guard"],
        "當你忍不住想再傳一段或一直確認已讀，這次就先停在原地",
        "如果等待回覆已經讓你無法專心生活，先不要再增加新訊息",
        "只要你開始用新訊息消除焦急，就先暫停這次聯絡",
    ),
    "self-blame-guard": (
        STOP_COPY["self-blame-guard"],
        "當你開始覺得只要自己做得更好就能挽回一切，就先停止聯絡",
        "如果反省又變成否定自己，先不要繼續道歉或補救",
        "只要這一步讓你把兩個人的問題全背在自己身上，就先停下來",
        "如果你為了得到回應又開始否定自己的價值，就不再往下補救",
    ),
    "stability-first": (
        STOP_COPY["stability-first"],
        "如果聯絡後連續幾天都無法睡覺或工作，先把關係動作暫停",
        "當這次互動明顯打亂你的生活，先恢復自己的節奏再做判斷",
        "只要你的情緒持續失控，就不再安排下一次聯絡",
    ),
    "safety-first": (
        STOP_COPY["safety-first"],
        "出現恐嚇、跟蹤或人身危險時，不再私下接觸並立即尋求協助",
        "只要你覺得人身安全受到威脅，這段互動就必須停止",
        "若對方有騷擾、控制或威脅行為，先保留證據並找可信任的協助",
    ),
    "standard": (
        STOP_COPY["standard"],
        "對方明確說不想談、不再回應或口氣更緊時，這次就停下",
        "如果這個做法讓他明顯退得更遠，不要立即再試另一種方法",
        "只要回應比原本更冷或出現拒絕，就不再往前推",
    ),
    "standard-boundary": (
        STOP_COPY["standard-boundary"],
        "對方再次說明不想聯絡時，就不要用其他方式靠近",
        "如果原本允許的聯絡方式也被關上，這次嘗試必須結束",
        "只要對方明確拒絕或收緊界線，就回到不主動聯絡",
    ),
}

ACTION_RATIONALE_EXTRA = {
    "unknown": (
        "目前還看不出哪個問題最關鍵，所以這次只做能隨時停下來的一步",
        "還看不清主要原因時，這次只做不會要求對方回答的事",
        "資料還不能指出唯一原因，所以先選不會增加聯絡壓力的做法",
    ),
    "communication-repair": (
        "你們不是沒有話說，而是一急著處理重要問題，就容易聽錯彼此的重點",
        "你越想一次說完，他越可能先聽見壓力，誤會也因此越解釋越多",
        "彼此都想讓對方理解自己，但語氣一緊，對話就容易變成各說各話",
        "這段互動容易卡在說得太多、聽得太少，所以重點要先縮到一件事",
        "誤會一出現，兩邊都可能急著解釋，反而沒有人先確認對方聽到什麼",
        "重要話題常因為補充太快而變重，對話需要一個清楚的停點",
        "你們不一定沒有溝通能力，只是情緒一高，就很難把同一句話聽完",
        "話題一多，你們就容易各自抓住不同重點，最後沒有處理原本的問題",
        "彼此都急著證明自己沒有惡意時，對話反而容易失去理解對方的空間",
        "每次都急著把話補完整時，對方更容易只聽見壓力，所以這次先停在重點",
        "對話最容易壞在雙方同時解釋，這次先讓一件事真正被聽懂",
        "你想說清楚時容易一次放進太多內容，這次只留下對方能回應的一點",
        "你越急著補充，他越難抓住真正重點，所以這次只說一件事",
        "這段關係常卡在解釋過多，下一步要讓這次的話有明確終點",
        "想把誤會一次說完時，兩邊反而更難聽懂，這次只修正最重要的一句",
    ),
    "outer-intensity": (
        "感受越強烈，越容易用想像補上沒有發生的部分，所以這次要回到看得見的反應",
        "一時靠近很容易放大期待，下一步只看對方之後是否還會靠近",
        "很在意對方時更需要簡單做法，才不會先把希望當成答案",
    ),
    "identity-rhythm": (
        "一方感到被否定時會先保護自己，對話也容易從事件變成對人的評價",
        "只要話題變成誰對誰錯，兩邊就很難再聽見真正需要",
        "彼此都想保住自尊時，下一步要避開評價整個人",
    ),
    "emotional-safety": (
        "安全感不足時，一個小反應就可能被聽成拒絕，對話因此更難放鬆",
        "兩個人都在防備時，先降低壓力比多解釋更有用",
        "氣氛一緊就容易互相誤解，所以這次開口要讓人能安心停下",
    ),
    "saturn-pressure": (
        "話題一碰到責任或承諾，其中一方就容易先考慮距離和風險",
        "一次談完整未來會讓壓力變重，這次只處理眼前能做到的事",
        "他先想到負擔和後果時，具體的小安排比口頭保證更容易回應",
    ),
    "action-conflict": (
        "兩邊都想快點解決時，口氣往往比問題本身更快變硬",
        "你們一著急就容易互相頂住，所以這次要先留出停點",
        "兩個人都急著處理時，小事也可能變成爭執，所以這次只談一件事",
    ),
    "attraction-pursuit": (
        "好感來得快時，很容易把當下的熱度當成關係已經往前",
        "靠近順利不等於關係已經確定，這次只看他會不會自然接下去",
        "熱度很高時更要少做一步，才能看出對方是否也想維持互動",
    ),
    "jupiter-support": (
        "彼此很會給希望和鼓勵，但真正差別在於支持有沒有被做完",
        "好聽的期待很多時，下一步要選一件真的能完成的事",
        "你們不缺一起變好的想像，現在要用具體行動確認好意",
    ),
    "slow-safety": (
        "這段互動需要可預期的節奏，任何突然加快都可能讓安全感退回去",
        "信任要靠幾次穩定互動累積，這次不適合突然增加內容",
        "越想讓關係快點確定，越需要先維持容易做到的小節奏",
    ),
}


def action_rationale_variants(value_key: str) -> tuple[str, ...]:
    return ACTION_RATIONALE_EXTRA[value_key]


def action_page_rationale_variants(value_key: str) -> tuple[str, ...]:
    """Return action-focused reasons without repeating fit or answer copy."""

    return ACTION_RATIONALE_EXTRA[value_key]


NEXT_MOVE_COPY = {
    "boundary-only": "現在先不主動聯絡，也不要改用其他方式接近",
    "observe-or-single-low-stimulation-test": "如果原本仍能聯絡，只送出一則簡短而沒有要求的訊息",
    "shared-space-boundary": "見面時只維持禮貌和必要交流，不在共同場合追問感情",
    "small-bid-response-led": "只開一個容易回答的小話題，說完就停",
    "tone-repair-in-existing-channel": "在原本的聯絡裡只澄清一件具體誤會",
}

ACTION_MODE_RELATIONAL = {
    "boundary-only": "維持不主動聯絡，直到他自己重開原本的聯絡方式",
    "observe-or-single-low-stimulation-test": "只保留一次輕鬆開口，之後把是否延續留給他決定",
    "shared-space-boundary": "共同場合只做必要交流，感情問題留到彼此都同意再談",
    "small-bid-response-led": "只提出一個小話題，說完讓他決定是否接下去",
    "tone-repair-in-existing-channel": "只澄清一件具體誤會，說完不追問關係結果",
}

ACTION_MODE_FORMS = {
    key: RealizationForms(
        NEXT_MOVE_COPY[key],
        ACTION_MODE_COPY[key][1],
        ACTION_MODE_RELATIONAL[key],
    )
    for key in NEXT_MOVE_COPY
}

ACTION_COMMAND_VARIANTS = {
    "boundary-only": (
        "現在先停止所有主動聯絡，也不要改用其他方式靠近",
        "先不要傳訊息或請別人代為聯絡，等他自己重開原本方式",
        "這一步就是不再開口，直到他主動改變聯絡界線",
        "先停下所有主動接近，不用換帳號或共同朋友試探",
        "目前不要再做任何聯絡動作，把是否重開管道留給他",
        "今天開始先不主動開口，也不透過任何人傳話給他",
        "把所有想傳的訊息先停住，只有他重開聯絡才重新判斷",
        "目前只做一件事，就是不再主動接近或測試他的界線",
    ),
    "observe-or-single-low-stimulation-test": (
        "如果原本仍能聯絡，只傳一則簡短訊息，送出後就停",
        "只用原本方式開口一次，訊息不問感情結果，說完就停",
        "先傳一件容易回答的日常小事，對方沒接就不要補訊息",
        "這次只留一則沒有要求的訊息，之後不再主動延長對話",
        "用一句簡短問候開口，送出後讓聯絡自然停下",
        "若原本管道仍開放，只傳一次簡短問候，之後不要追問",
        "只用一則日常訊息確認能否說話，沒有回覆就停",
        "這次開口控制在一句話，傳完不再補充或換話題",
    ),
    "shared-space-boundary": (
        "見面時只處理工作或日常，感情對話先不要開口",
        "共同場合只保留必要互動，不利用碰面追問關係",
        "這次見面只做原本需要做的事，不另外開啟感情話題",
        "工作或日常交流保持簡短，想談關係先等彼此另外同意",
        "在共同空間只維持禮貌互動，不把現場變成感情對話",
        "共同場合只完成必要往來，離開現場後也不追著談關係",
        "見面只說工作或生活需要，其他感情問題先不要開口",
        "這一步只維持基本禮貌，不用碰面機會測試他的態度",
    ),
    "small-bid-response-led": (
        "只用一則訊息開一個容易回答的小話題，說完就停",
        "這次只問一件日常小事，對方回覆後不要立刻加重話題",
        "用一句容易接的話開口，讓他的回覆決定對話要不要繼續",
        "只提出一個簡單問題，沒有自然回應就停在這一步",
        "先傳一則短訊息看看能否自然對話，不追問感情結果",
        "只開一個能用一句話回答的話題，回覆很短就停",
        "先用簡短訊息問一件日常小事，不把回覆帶到感情問題",
        "這一步只傳一次，讓他是否接話決定後面還有沒有對話",
    ),
    "tone-repair-in-existing-channel": (
        "在原本對話裡只澄清一件誤會，說完就停",
        "先用一則短訊息修正最重要的說法，不補整段關係解釋",
        "這次只為一件具體的話道歉或說明，不要求對方立刻回覆",
        "把原本說重的那一句重新說清楚，其他問題先不要帶進對話",
        "只處理最近一次誤會，訊息送出後不要再追問結果",
        "在原本管道把那句重話改說清楚，說完不再要求回應",
        "只傳一則短訊息承認具體問題，不延伸成整段關係說明",
        "這一步只修正最近的說法，對方沒有接話就停",
    ),
}

ACTION_PURPOSE_VARIANTS = {
    "boundary-only": (
        "這一步的目的是先守住他目前的聯絡界線，不再另外找方法靠近",
    ),
    "observe-or-single-low-stimulation-test": (
        "這一步只確認原本的聯絡方式是否仍被接受，不處理感情結果",
    ),
    "shared-space-boundary": (
        "這一步先保護共同生活或工作的空間，不在碰面時處理感情問題",
    ),
    "small-bid-response-led": (
        "這一步只確認你們能不能自然說上幾句，不同時確認關係",
    ),
    "tone-repair-in-existing-channel": (
        "這一步只修正最近的一個誤會，不要求他同時回答整段關係",
    ),
}

COMPLETION_BOUNDARY_VARIANTS = {
    "boundary-only": (
        "你停止主動聯絡，也沒有改用其他方式接近，這一步就完成了",
    ),
    "observe-or-single-low-stimulation-test": (
        "訊息只送一次，送出後沒有補充或追問，這一步就完成了",
    ),
    "shared-space-boundary": (
        "共同場合只留下必要交流，沒有追問感情，這一步就完成了",
    ),
    "small-bid-response-led": (
        "一個小話題說完後停下，不再加重內容，這一步就完成了",
    ),
    "tone-repair-in-existing-channel": (
        "一件誤會澄清完就停下，沒有追問關係結果，這一步就完成了",
    ),
}

BLOCKED_ACTION_INFINITIVES = {
    "alternate-account-contact": "改用其他帳號聯絡",
    "asking-for-answer-now": "要求他現在就回答",
    "emotional-confrontation": "在情緒很滿時攤牌",
    "forcing-relationship-definition": "逼他立刻定義關係",
    "long-explanation": "傳出很長的解釋",
    "long-pressure-message": "用長訊息施壓",
    "public-confrontation": "在公開或共同場合談判",
    "rapid-escalation": "短時間內連續加重話題",
    "relationship-definition-push": "追問關係定位",
    "repeated-messages": "補傳第二則訊息",
    "testing-loyalty": "故意試探他在不在乎",
    "third-party-pressure": "請朋友代為施壓",
    "turning-reply-into-commitment": "把一次回覆當成承諾",
    "using-shared-space-as-pressure": "利用共同場合逼他談關係",
}

BLOCKED_STOP_TEMPLATES = {
    "anxiety-guard": (
        "如果焦急讓你想{action}，這次就先停，不要再加新的動作",
        "只要你忍不住想{action}，先離開訊息畫面，今天不再聯絡",
        "如果等待回覆讓你開始{action}，這一步就到此為止",
    ),
    "self-blame-guard": (
        "如果你因為自責而想{action}，先停下來，不要把問題全扛在自己身上",
        "只要你覺得必須靠{action}才能補救一切，這次就不要做",
        "如果反省讓你又想{action}，先照顧自己，不再追加聯絡",
    ),
    "stability-first": (
        "如果{action}已經讓你睡不好或無法專心，就先暫停這次聯絡",
        "只要你為了{action}明顯失去生活節奏，下一步就先停止",
        "如果這次互動讓你反覆想{action}，先回到自己的日常再判斷",
    ),
    "standard": (
        "如果他已經回得更短或明確拒絕，就不要再{action}",
        "只要他的口氣變硬或不再回應，這次就停止{action}",
        "如果這一步讓他退得更遠，就先停止，不要再嘗試{action}",
    ),
    "standard-boundary": (
        "如果他再次收緊聯絡界線，就不要再{action}",
        "只要原本的聯絡方式被關上，立即停止{action}",
        "如果他明確說不想聯絡，就不再嘗試{action}",
    ),
}


def blocked_stop_variants(stop: str, blocked_action: str) -> tuple[str, ...]:
    if stop == "safety-first":
        return STOP_VARIANTS[stop]
    templates = BLOCKED_STOP_TEMPLATES[stop]
    action = BLOCKED_ACTION_INFINITIVES[blocked_action]
    return tuple(template.format(action=action) for template in templates)


def single_fact(facts: SectionFactReader, role: str) -> dict[str, Any]:
    records = facts.records(role)
    if len(records) != 1:
        raise FinalNarrativeSemanticCoverageError(
            f"{facts.section_id}: expected one {role} fact, got {len(records)}"
        )
    return records[0]


def render_action_direction(facts: SectionFactReader, seed: str) -> dict[str, str]:
    del seed
    question_fact = single_fact(facts, "question")
    contact_fact = single_fact(facts, "contact-status")
    purpose_fact = single_fact(facts, "action-purpose")
    mode_fact = single_fact(facts, "action-mode")
    completion_fact = single_fact(facts, "completion-boundary")
    repair_fact = single_fact(facts, "repair-lever")
    stop_fact = single_fact(facts, "stop-condition")
    contact_posture_fact = single_fact(facts, "contact-posture")
    blocked_facts = facts.records("blocked-action")

    question = str(question_fact.get("valueKey") or "")
    contact = str(contact_fact.get("valueKey") or "")
    purpose_mode = str(purpose_fact.get("valueKey") or "")
    mode = str(mode_fact.get("valueKey") or "")
    completion_mode = str(completion_fact.get("valueKey") or "")
    repair = str(repair_fact.get("valueKey") or "")
    stop = str(stop_fact.get("valueKey") or "")
    contact_posture = str(contact_posture_fact.get("valueKey") or "")
    blocked_values = [str(item.get("valueKey") or "") for item in blocked_facts]

    require_supported_value(section_id=facts.section_id, role="question", value=question, supported=QUESTION_KEYS)
    require_supported_value(
        section_id=facts.section_id,
        role="contact-status",
        value=contact,
        supported=CONTACT_STATUS_KEYS,
    )
    require_supported_value(
        section_id=facts.section_id,
        role="action-purpose",
        value=purpose_mode,
        supported=set(ACTION_PURPOSE_VARIANTS),
    )
    require_supported_value(
        section_id=facts.section_id,
        role="action-mode",
        value=mode,
        supported=set(ACTION_MODE_FORMS),
    )
    require_supported_value(
        section_id=facts.section_id,
        role="completion-boundary",
        value=completion_mode,
        supported=set(COMPLETION_BOUNDARY_VARIANTS),
    )
    require_supported_value(
        section_id=facts.section_id,
        role="repair-lever",
        value=repair,
        supported={*RELATIONSHIP_DYNAMIC_KEYS, "unknown"},
    )
    require_supported_value(
        section_id=facts.section_id,
        role="stop-condition",
        value=stop,
        supported=set(STOP_COPY),
    )
    require_supported_value(
        section_id=facts.section_id,
        role="contact-posture",
        value=contact_posture,
        supported=set(CONTACT_POSTURE_TAGS),
    )
    for blocked in blocked_values:
        require_supported_value(
            section_id=facts.section_id,
            role="blocked-action",
            value=blocked,
            supported=set(BLOCKED_ACTION_COPY),
        )
    if not blocked_values:
        raise FinalNarrativeSemanticCoverageError("action-direction: required blocked-action facts are missing")
    if contact == "blocked" and mode != "boundary-only":
        raise FinalNarrativeSemanticCoverageError(
            "action-direction: blocked contact must use boundary-only mode"
        )
    if purpose_mode != mode or completion_mode != mode:
        raise FinalNarrativeSemanticCoverageError(
            "action-direction: purpose and completion boundary must follow the selected action"
        )
    if repair == "unknown":
        facts.record_unknown_fallback(
            "repair-lever",
            repair,
            "repair-lever-unknown",
        )

    mode_domain = tuple(ACTION_MODE_FORMS)
    repair_domain = (*RELATIONSHIP_DYNAMIC_KEYS, "unknown")
    stop_domain = tuple(STOP_COPY)
    posture_domain = tuple(CONTACT_POSTURE_TAGS)
    blocked_domain = tuple(BLOCKED_ACTION_COPY)
    question_index = domain_index(question, QUESTION_KEYS, identity="action-direction:question")
    contact_index = domain_index(
        contact,
        CONTACT_STATUS_KEYS,
        identity="action-direction:contact-status",
    )
    mode_index = domain_index(
        mode,
        mode_domain,
        identity="action-direction:action-mode",
    )
    domain_index(repair, repair_domain, identity="action-direction:repair-lever")
    stop_index = domain_index(
        stop,
        stop_domain,
        identity="action-direction:stop-condition",
    )
    domain_index(
        contact_posture,
        posture_domain,
        identity="action-direction:contact-posture",
    )
    selected_blocked = select_context_variant(
        blocked_values,
        stop_index,
        identity="action-direction:selected-blocked-action",
    )
    selected_blocked_index = domain_index(
        selected_blocked,
        blocked_domain,
        identity="action-direction:blocked-action",
    )
    caution_index = stop_index * len(blocked_domain) + selected_blocked_index
    headline = select_context_variant(
        QUESTION_HEADLINES[question],
        question_index,
        identity="action-direction:question-headline",
    )
    purpose = select_context_variant(
        ACTION_PURPOSE_VARIANTS[purpose_mode],
        contact_index,
        identity="action-direction:action-purpose",
    )
    completion = select_context_variant(
        COMPLETION_BOUNDARY_VARIANTS[completion_mode],
        contact_index,
        identity="action-direction:completion-boundary",
    )
    next_move = select_context_variant(
        ACTION_COMMAND_VARIANTS[mode],
        mode_index,
        identity="action-direction:action-mode",
    )
    caution = select_context_variant(
        blocked_stop_variants(stop, selected_blocked),
        caution_index,
        identity="action-direction:stop-condition",
    )
    rendered = {
        "headline": headline,
        "meaning": join_sentences(purpose),
        "body": join_sentences(completion),
        "nextMove": join_sentences(next_move),
        "caution": join_sentences(caution),
    }
    frames: dict[str, ReaderMeaningFrame] = {
        "question": frame_from_fact(
            question_fact,
            scene_key="action-focus",
            purpose="direct",
            certainty="observed",
        ),
        "purpose": frame_from_fact(
            purpose_fact,
            scene_key=f"action-purpose.{contact}",
            purpose="direct",
            certainty="conditional",
        ),
        "completion": frame_from_fact(
            completion_fact,
            scene_key=f"completion-boundary.{contact}",
            purpose="direct",
            certainty="conditional",
        ),
        "mode": frame_from_fact(
            mode_fact,
            scene_key=f"one-action.{contact}",
            purpose="direct",
            certainty="conditional",
        ),
        "stop": frame_from_fact(
            stop_fact,
            scene_key=f"stopping-condition.{selected_blocked}",
            purpose="direct",
            certainty="conditional",
        ),
    }
    plan_steps = [
        ("headline", frames["question"]),
        ("opening", frames["purpose"]),
        ("condition", frames["completion"]),
        ("action", frames["mode"]),
        ("boundary", frames["stop"]),
    ]
    plan = paragraph_plan(
        section_id=facts.section_id,
        paragraph_kind="one-action-completion-boundary",
        conclusion_key=f"{question}-{contact}-{mode}-{stop}",
        steps=plan_steps,
        supports=(
            support_from_fact(contact_fact),
            support_from_fact(repair_fact),
            support_from_fact(contact_posture_fact),
            *(support_from_fact(item) for item in blocked_facts),
        ),
    )
    validate_action_rendered(
        rendered,
        frames=frames,
        selected_blocked=selected_blocked,
        stop=stop,
    )
    validate_paragraph_output(plan, rendered)
    return rendered


def split_sentences(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[。！？!?]+", value) if item.strip()]


@lru_cache(maxsize=1)
def action_sentence_traces() -> dict[str, dict[str, str]]:
    traces: dict[str, dict[str, str]] = {}

    def add(text: str, trace: dict[str, str]) -> None:
        normalized = normalize_copy(text)
        existing = traces.get(normalized)
        if existing is not None and existing != trace:
            raise ActionDirectionNativeChineseError(
                f"action sentence has ambiguous trace: {text}"
            )
        traces[normalized] = trace

    for question, values in QUESTION_HEADLINES.items():
        for text in values:
            add(
                text,
                {
                    "kind": "fact-realization",
                    "role": "question",
                    "valueKey": question,
                    "purpose": "direct",
                },
            )
    for mode, values in ACTION_PURPOSE_VARIANTS.items():
        for text in values:
            add(
                text,
                {
                    "kind": "fact-realization",
                    "role": "action-purpose",
                    "valueKey": mode,
                    "purpose": "direct",
                },
            )
    for mode, values in COMPLETION_BOUNDARY_VARIANTS.items():
        for text in values:
            add(
                text,
                {
                    "kind": "fact-realization",
                    "role": "completion-boundary",
                    "valueKey": mode,
                    "purpose": "direct",
                },
            )
    for repair, values in ACTION_RATIONALE_EXTRA.items():
        for text in values:
            add(
                text,
                {
                    "kind": "fact-realization",
                    "role": "repair-lever",
                    "valueKey": repair,
                    "purpose": "situational",
                },
            )
    for posture, values in OBSERVABLE_RESPONSE_VARIANTS.items():
        for text in values:
            add(
                text,
                {
                    "kind": "fact-realization",
                    "role": "contact-posture",
                    "valueKey": posture,
                    "purpose": "relational",
                },
            )
    for mode, values in ACTION_COMMAND_VARIANTS.items():
        for text in values:
            add(
                text,
                {
                    "kind": "fact-realization",
                    "role": "action-mode",
                    "valueKey": mode,
                    "purpose": "direct",
                },
            )
    for text in STOP_VARIANTS["safety-first"]:
        add(
            text,
            {
                "kind": "fact-realization",
                "role": "stop-condition",
                "valueKey": "safety-first",
                "purpose": "direct",
            },
        )
    for stop in BLOCKED_STOP_TEMPLATES:
        for blocked_action in BLOCKED_ACTION_INFINITIVES:
            for text in blocked_stop_variants(stop, blocked_action):
                add(
                    text,
                    {
                        "kind": "composition",
                        "role": "stop-condition",
                        "valueKey": stop,
                        "purpose": "direct",
                        "contributorRole": "blocked-action",
                        "contributorValueKey": blocked_action,
                    },
                )
    return traces


def action_sentence_trace(sentence: str) -> dict[str, str] | None:
    return action_sentence_traces().get(normalize_copy(sentence))


def assert_frame_trace(
    text: str,
    frame: ReaderMeaningFrame,
    *,
    purpose: str,
) -> dict[str, str]:
    sentences = split_sentences(text)
    if len(sentences) != 1:
        raise ActionDirectionNativeChineseError(
            f"action sentence ownership is ambiguous: {text}"
        )
    trace = action_sentence_trace(sentences[0])
    if trace is None:
        raise ActionDirectionNativeChineseError(
            f"untraceable action sentence: {sentences[0]}"
        )
    if (
        trace.get("role") != frame.role
        or trace.get("valueKey") != frame.value_key
        or trace.get("purpose") != purpose
    ):
        raise ActionDirectionNativeChineseError(
            f"action sentence trace does not match frame: {trace}"
        )
    return trace


def validate_action_rendered(
    rendered: Mapping[str, str],
    *,
    frames: Mapping[str, ReaderMeaningFrame],
    selected_blocked: str,
    stop: str,
) -> None:
    for frame in frames.values():
        frame.validate()
        if frame.section_id != "action-direction":
            raise ActionDirectionNativeChineseError(
                f"action renderer received frame for {frame.section_id}"
            )
    for field, text in rendered.items():
        issues = audit_native_zh_tw_text(text)
        if issues:
            details = ", ".join(f"{item.severity}:{item.id}" for item in issues)
            raise ActionDirectionNativeChineseError(
                f"action-direction:{field}: native Chinese gate failed: {details}"
            )
        abstraction_hits = [
            phrase for phrase in FORBIDDEN_ACTION_ABSTRACTIONS if phrase in text
        ]
        if abstraction_hits:
            raise ActionDirectionNativeChineseError(
                f"action-direction:{field}: abstract action language: {abstraction_hits}"
            )
        if len(split_sentences(text)) != 1:
            raise ActionDirectionNativeChineseError(
                f"action-direction:{field}: each field must contain one sentence"
            )
    if "完成" not in rendered["body"]:
        raise ActionDirectionNativeChineseError(
            "action-direction:body must state when the action is complete"
        )
    if not re.search(r"如果|只要|當|若|出現", rendered["caution"]):
        raise ActionDirectionNativeChineseError(
            "action-direction:caution must state a stopping condition"
        )
    if not re.search(
        r"停止|不要|不再|只傳|只用|先傳|見面|維持|澄清|修正|道歉|說明|處理|開口|問|停",
        rendered["nextMove"],
    ):
        raise ActionDirectionNativeChineseError(
            "action-direction:nextMove lacks one concrete command"
        )

    assert_frame_trace(rendered["headline"], frames["question"], purpose="direct")
    assert_frame_trace(rendered["meaning"], frames["purpose"], purpose="direct")
    assert_frame_trace(rendered["body"], frames["completion"], purpose="direct")
    assert_frame_trace(rendered["nextMove"], frames["mode"], purpose="direct")
    caution_trace = assert_frame_trace(
        rendered["caution"],
        frames["stop"],
        purpose="direct",
    )
    if stop == "safety-first":
        if caution_trace.get("contributorRole"):
            raise ActionDirectionNativeChineseError(
                "safety stopping condition unexpectedly depends on blocked action"
            )
    elif (
        caution_trace.get("contributorRole") != "blocked-action"
        or caution_trace.get("contributorValueKey") != selected_blocked
    ):
        raise ActionDirectionNativeChineseError(
            "action caution lost its selected blocked-action fact"
        )


def action_catalog_errors() -> list[str]:
    try:
        traces = action_sentence_traces()
    except ActionDirectionNativeChineseError as exc:
        return [str(exc)]
    errors: list[str] = []
    for normalized, trace in traces.items():
        del trace
        issues = audit_native_zh_tw_text(normalized)
        if issues:
            errors.append(
                f"{normalized}: "
                + ", ".join(f"{item.severity}:{item.id}" for item in issues)
            )
        abstraction_hits = [
            phrase for phrase in FORBIDDEN_ACTION_ABSTRACTIONS if phrase in normalized
        ]
        if abstraction_hits:
            errors.append(f"{normalized}: abstract action language {abstraction_hits}")
    return errors


__all__ = [
    "ACTION_COMMAND_VARIANTS",
    "ACTION_PURPOSE_VARIANTS",
    "ACTION_DIRECTION_NATIVE_ZH_TW_CATALOG_VERSION",
    "ACTION_MODE_FORMS",
    "COMPLETION_BOUNDARY_VARIANTS",
    "ACTION_RATIONALE_EXTRA",
    "ActionDirectionNativeChineseError",
    "BLOCKED_ACTION_INFINITIVES",
    "OBSERVABLE_RESPONSE_VARIANTS",
    "STOP_VARIANTS",
    "action_catalog_errors",
    "action_page_rationale_variants",
    "action_rationale_variants",
    "action_sentence_trace",
    "action_sentence_traces",
    "blocked_stop_variants",
    "render_action_direction",
    "validate_action_rendered",
]
