"""Fact-only Traditional Chinese renderer for the five paid reading sections."""

from __future__ import annotations

import re
from typing import TypedDict

from .final_narrative_fact_contract import ValidatedFinalNarrativeFactContract
from .final_narrative_page_grammar import validate_page_grammar
from .final_narrative_realization import RealizationForms, RealizationPurpose
from .final_narrative_semantic_coverage import SectionFactReader
from .final_narrative_semantic_domains import (
    PLANET_FUNCTIONS,
    RelationshipSignal,
    parse_relationship_signal,
)


FINAL_NARRATIVE_FACT_RENDERER_VERSION = "final-narrative-zh-tw-fact-renderer-v7"


class RenderedReaderSection(TypedDict):
    headline: str
    meaning: str
    body: str
    nextMove: str
    caution: str


MOON_NEEDS = {
    "aries": ("你需要對方直接回應，不喜歡在猜測裡等太久", "你有感覺時希望事情說開，拖著不談會讓你更不安"),
    "taurus": ("你很看重穩定和可預期，答應的事有做到才會安心", "你會從持續的陪伴和實際行動確認一個人是否可靠"),
    "gemini": ("你需要有來有往的對話，話能流動時才容易靠近", "你會透過聊天整理感受，長時間沒有交流容易讓你想很多"),
    "cancer": ("你需要被在意和照顧，對方記得小事會讓你很安心", "你對冷熱變化很敏感，需要熟悉而溫和的回應"),
    "leo": ("你需要感覺自己被重視，也希望付出能被對方看見", "對方願意明確肯定你時，你會更自然地表達感情"),
    "virgo": ("你會從日常細節確認對方是否可靠，答應的事有做到才容易安心", "你重視有交代的日常，事情處理得妥當比好聽的話更重要"),
    "libra": ("你希望彼此願意商量，兩個人都有決定空間才會安心", "你在意相處是否公平，也需要對話保留彼此的台階"),
    "scorpio": ("你需要真誠和深度信任，表面的安撫很難讓你放心", "你一旦在意就會很深，也會特別留意對方有沒有隱瞞"),
    "sagittarius": ("你需要坦白和空間，不喜歡用控制換取安全感", "你希望關係能誠實談方向，也能保留各自的生活"),
    "capricorn": ("你重視責任和長期可靠，看見持續承擔才會真正安心", "你要看到對方願意負責和安排未來，才會逐漸信任"),
    "aquarius": ("你需要被尊重，也希望兩個人能像朋友一樣理解彼此", "你重視個人空間，能平靜談話時，你反而更願意靠近"),
    "pisces": ("你很容易感受到氣氛和情緒，需要溫柔而真誠的回應", "你會自然體會對方的感受，但界線不清時也容易受影響"),
}

MERCURY_STYLES = {
    "aries": ("你表達重要事情時很直接，希望問題不要拖太久", "你習慣先講重點，對方回得太慢時容易變得著急"),
    "taurus": ("你需要時間想清楚，一旦決定就不喜歡反覆改口", "你傾向把話說得實際，也希望對方給出明確做法"),
    "gemini": ("你會在表達過程中整理想法，對話裡常會想到新的角度", "你需要有來有往地說話，話題停太久時，心裡容易冒出很多問題"),
    "cancer": ("你表達時很在意對方的口氣，先感覺被理解才願意繼續談", "你說話會帶著感受，語氣一重就容易先把心收起來"),
    "leo": ("你希望自己的表達被尊重，一覺得被否定就很難繼續談", "你表達時有明確立場，也需要對方認真聽完"),
    "virgo": ("你表達時會把問題一項一項說清楚，但對方有時會聽成你在挑錯", "你在意細節和邏輯，說法不清楚時會想立刻修正"),
    "libra": ("有分歧時，你會先找兩邊都能接受的表達方式", "你希望對話保留尊重，不喜歡被逼著當場選邊"),
    "scorpio": ("你表達時想談真正原因，不喜歡用幾句好聽話帶過", "你會追問話背後的意思，含糊的回答很難讓你停止猜測"),
    "sagittarius": ("你表達時喜歡坦白談大方向，不喜歡繞著真正問題說話", "你說話直率，也需要彼此能容納不同看法"),
    "capricorn": ("你表達事情時重視實際做法和責任，不太相信口頭保證", "你習慣先釐清安排與後果，再決定要不要往前"),
    "aquarius": ("你需要先把想法整理好，才願意把重要的話說清楚", "你傾向拉開一點距離思考，不喜歡在情緒裡被逼答覆"),
    "pisces": ("對方的語氣和當下氣氛很容易影響你怎麼表達", "說得溫和而清楚時，你比較能把真正的感受說出來"),
}

PRESSURE_RESPONSES = {
    "aries": ("他有壓力時容易立刻反應，話還沒說完就可能做決定", "先讓情緒降下來，再談真正要處理的事"),
    "taurus": ("他有壓力時容易守住原本立場，不想先退一步", "他開始重複同一個立場時，先暫停話題"),
    "gemini": ("他有壓力時容易越說越多，原本一件事會拉出很多支線", "話題變散時，先回到最初那個問題"),
    "cancer": ("他有壓力又覺得被責怪時，會先顧著保護自己", "談現在的事時，不要把以前的不愉快全部拉進來"),
    "leo": ("他有壓力又覺得被否定時，會先維護自尊", "對話變成輸贏時，先回到具體發生的事情"),
    "virgo": ("他有壓力又想解決問題時，容易一直抓著字句和對錯", "兩個人開始修正彼此說法時，先問真正介意的是什麼"),
    "libra": ("他有壓力時常先忍著維持和平，累積久了又可能突然說重話", "他從沉默轉成強硬時，先停下來讓情緒回穩"),
    "scorpio": ("事情碰到信任時，他的反應容易特別強烈", "先把事實和界線說清楚，不要替彼此猜動機"),
    "sagittarius": ("他有壓力又覺得被限制時，容易反抗或直接離開談話", "他開始想逃開時，先停止加壓"),
    "capricorn": ("他有壓力時會先考慮責任和後果，回應也可能變慢", "把問題拆成能做到的安排，比要求當場承諾有效"),
    "aquarius": ("他有壓力又覺得情緒太重時，容易先離開對話", "他拉開距離時，先給空間，不要追著要答案"),
    "pisces": ("他感到壓力時容易先退回自己的情緒裡", "先說清楚一件具體事情，不要要求他同時處理所有感受"),
}

MOON_NEED_RELATIONAL = {
    "aries": "你越在意一段關係，越需要對方直接回應；長時間沒有答案會讓你更想立刻確認",
    "taurus": "對方持續做到答應的事，你才會逐漸放心；只有一時熱情很難讓你真正安定",
    "gemini": "你會在有來有往的對話裡靠近；話一停太久，猜測就容易取代真實交流",
    "cancer": "對方記得你的感受和小事，你會更願意靠近；冷熱反覆則容易讓你先縮回去",
    "leo": "你感覺自己的付出被看見時會更願意表達；被忽略時，自尊會先擋住真正需要",
    "virgo": "對方把日常事情處理好，你才容易信任；細節反覆失約會讓你比一句重話更不安",
    "libra": "兩個人願意商量時你會比較安心；只由一方決定，會讓你慢慢失去靠近的意願",
    "scorpio": "關係越重要，你越需要真誠和深度；含糊或隱瞞會讓你反覆確認對方是否可信",
    "sagittarius": "坦白和空間同時存在時，你最能自然靠近；被控制時，你會先保護自己的自由",
    "capricorn": "對方願意承擔並安排未來，你才會逐漸交付信任；口頭保證很難取代實際責任",
    "aquarius": "彼此尊重空間又能平靜談話時，你反而更願意親近；情緒逼迫會讓你先拉開距離",
    "pisces": "溫柔而清楚的回應會讓你願意打開感受；界線模糊時，你也容易把對方情緒全攬進來",
}

MERCURY_STYLE_RELATIONAL = {
    "aries": "你越想解決問題，話會越直接；對方如果需要時間，兩個人的速度就容易撞在一起",
    "taurus": "你會先想清楚再表態，也希望說過的話能落實；反覆改口會讓你更難繼續相信",
    "gemini": "你靠對話整理想法，對方願意接話時你會越說越清楚；突然沉默則容易讓問題越想越多",
    "cancer": "你先感覺被理解，才說得出真正重點；口氣一重，你和對方就容易只剩下保護自己",
    "leo": "對方認真聽完時，你會更願意說出柔軟的一面；一覺得被否定，立場就容易變得更硬",
    "virgo": "你想把細節釐清，對方卻可能聽成挑錯；如果沒有先確認目的，解釋越多越容易緊張",
    "libra": "你習慣替彼此保留台階，對方越強硬，你越難當場說出真正不同意的地方",
    "scorpio": "你需要談到真正原因才會放心；對方越含糊，你越容易追問話背後還藏著什麼",
    "sagittarius": "你希望直接談方向，也需要容納不同看法；一旦覺得被限制，說話會變得更直",
    "capricorn": "你先談做法和後果，才相信問題能處理；對方只談感覺時，你們容易各自錯過重點",
    "aquarius": "你需要拉開一點距離整理想法；對方越催你當場回答，你越難把真正意思說完整",
    "pisces": "對方說得溫和而具體時，你比較能表達感受；氣氛混亂時，你容易先順著對方而沒有說清自己",
}

PRESSURE_RESPONSE_SITUATIONAL = {
    "aries": "重要話題突然變重時，他可能先回重話或立刻做決定，之後才慢慢整理真正感受",
    "taurus": "爭執一開始，他常會重複原本立場；繼續要求他立刻改口，只會讓僵持更久",
    "gemini": "他一緊張就可能同時談很多支線，原本要處理的那件事反而被越帶越遠",
    "cancer": "現在的話一碰到以前的不舒服，他會先顧著保護自己，很難立刻回到眼前問題",
    "leo": "他覺得自己被否定時，討論很快會變成尊嚴和輸贏，而不是原本發生的事情",
    "virgo": "他想解決問題時會一直修正字句，兩個人容易卡在誰說得正確，沒有談到真正介意",
    "libra": "他可能先沉默維持和平，累積到承受不了時才突然把不滿一次說重",
    "scorpio": "事情碰到信任或隱瞞時，他的反應會明顯變強，一件小事也可能被聽成背叛",
    "sagittarius": "他感覺自由被限制時，可能直接離開對話，不願意在當下繼續被要求表態",
    "capricorn": "一談責任和後果，他會先衡量自己能不能做到，因此回應常比你期待得慢",
    "aquarius": "情緒太滿時，他會先拉開距離整理自己；當下追問越多，他越不容易回來說清楚",
    "pisces": "很多感受同時湧上來時，他容易沉默或退開，沒有辦法一次處理所有人的情緒",
}

PRESSURE_RESPONSE_RELATIONAL = {
    "aries": "你越急著把話說完，他越可能先做出反應；最後兩個人都來不及聽懂真正問題",
    "taurus": "你越要求他立刻退讓，他越會守住原本立場；兩個人的僵持因此越拖越久",
    "gemini": "你越追著每個細節確認，他越容易把話題拉得更散；最後誰都沒有回答最初問題",
    "cancer": "你越急著確認現在，他越容易想起以前受過的傷；對話於是從眼前問題變成彼此防備",
    "leo": "你越想證明自己的道理，他越覺得被否定；最後討論會變成誰輸誰贏",
    "virgo": "你們越想把每句話修正到正確，越容易忽略真正受傷的地方，對話也就一直繞在字句上",
    "libra": "你以為他的沉默代表沒事，他卻可能一直累積不滿；等到爆發時，兩邊都覺得太突然",
    "scorpio": "你越用猜測確認他的動機，他越會保護自己的信任界線；原本的小事因此變得更強烈",
    "sagittarius": "你越急著限制他的選擇，他越想離開；最後距離感比原本要談的事情更大",
    "capricorn": "你越要求他當場承諾，他越會先退回責任和後果；回應因此變慢，也更保守",
    "aquarius": "你越急著拉他回到情緒裡，他越需要距離；最後你感到被冷落，他也感到沒有空間",
    "pisces": "你越希望他一次接住所有感受，他越容易沉默；最後兩個人都不知道該先處理哪一件事",
}

MOON_NEED_FORMS = {
    sign: RealizationForms(options[0], options[1], MOON_NEED_RELATIONAL[sign])
    for sign, options in MOON_NEEDS.items()
}
MERCURY_STYLE_FORMS = {
    sign: RealizationForms(options[0], options[1], MERCURY_STYLE_RELATIONAL[sign])
    for sign, options in MERCURY_STYLES.items()
}
PRESSURE_RESPONSE_FORMS = {
    sign: RealizationForms(
        PRESSURE_RESPONSES[sign][0],
        PRESSURE_RESPONSE_SITUATIONAL[sign],
        PRESSURE_RESPONSE_RELATIONAL[sign],
    )
    for sign in PRESSURE_RESPONSES
}

MOON_NEED_FORMS["unknown"] = RealizationForms(
    "目前只能先從實際相處確認你需要什麼才會安心",
    "出生資料不足時，先觀察哪些互動會讓你放鬆或不安",
    "你需要的安全感要由一段時間的真實反應確認，不能用缺少的星盤資料補答案",
)
MERCURY_STYLE_FORMS["unknown"] = RealizationForms(
    "目前資料不足，還不能用星盤判斷你習慣怎麼表達",
    "出生資料不足時，先看什麼說法最容易讓你們錯過重點",
    "你和對方怎麼說、怎麼聽，需要從真實對話確認，不能用缺少的資料替代",
)
PRESSURE_RESPONSE_FORMS["unknown"] = RealizationForms(
    "目前資料不足，還不能判斷他有壓力時會怎麼回應",
    "話題變重而資料不足時，先看他的回應是否明顯縮短",
    "你越急著確認、他是否越退開，需要由實際互動確認，不能先替他定型",
)

PARTNER_MOON_NEEDS = {
    "aries": "他需要直接而清楚的互動，不喜歡長時間猜測或等待",
    "taurus": "他需要穩定和可預期，會用持續行動確認關係是否可靠",
    "gemini": "他需要能自然聊天和交換想法，對話停住時容易拉開距離",
    "cancer": "他需要熟悉而溫和的回應，感到被責怪時會先保護自己",
    "leo": "他需要感覺自己的付出被看見，被否定時容易先維護自尊",
    "virgo": "他需要明確的說法，也會從細節確認彼此是否認真",
    "libra": "他需要彼此願意商量，太強硬的要求會讓他更難表態",
    "scorpio": "他需要深度信任，含糊或試探會讓他更難放心",
    "sagittarius": "他需要坦白和空間，被限制時容易先離開對話",
    "capricorn": "他需要看見現實安排和責任，口頭保證不容易讓他放心",
    "aquarius": "他需要被尊重和保留思考空間，情緒太滿時會先退開",
    "pisces": "他需要溫和而不帶壓迫的交流，氣氛太重時容易沉默",
}


def partnerize(text: str) -> str:
    return (
        text.replace("你們", "兩個人")
        .replace("對方情緒", "__USER_POSSESSIVE__情緒")
        .replace("對方", "__USER__")
        .replace("你的", "__PARTNER_POSSESSIVE__")
        .replace("你", "他")
        .replace("__PARTNER_POSSESSIVE__", "他的")
        .replace("__USER_POSSESSIVE__", "你的")
        .replace("__USER__", "你")
    )


PARTNER_MOON_NEED_FORMS = {
    sign: RealizationForms(
        PARTNER_MOON_NEEDS[sign],
        partnerize(MOON_NEED_FORMS[sign].situational),
        partnerize(MOON_NEED_FORMS[sign].relational),
    )
    for sign in PARTNER_MOON_NEEDS
}
PARTNER_MOON_NEED_FORMS["unknown"] = RealizationForms(
    "目前只能先從實際互動確認他在關係裡需要什麼",
    "資料不足時，先看什麼情況會讓他願意說得更多",
    "他需要的安全感要由一段時間的回應確認，不能先替他的內心下結論",
)

ARCHETYPES = {
    "unknown": ("暫時不替關係定型", "目前可用的合盤線索不足，還不能把你們歸到特定相處類型"),
    "past-life-intensity": ("前世因緣感型", "彼此很容易留下深刻感受，但強度不等於能走得長久"),
    "growth-support": ("命中貴人型", "你們有鼓勵彼此成長的條件，仍要看支持能不能落到日常"),
    "communication-repair": ("溝通修復型", "關係好不好，很大部分取決於誤會能不能被說開"),
    "mutual-activation": ("彼此牽動型", "兩個人的反應會互相影響，靠近與退開都容易被對方感受到"),
    "emotional-familiarity": ("靈魂伴侶型", "相處容易有熟悉感，也會放大彼此對安全感的需要"),
    "growth-through-friction": ("磨合成長型", "這段關係需要時間和實際調整，不能只靠感覺撐住"),
    "fast-spark-conflict": ("歡喜冤家型", "火花和摩擦都來得快，說話速度會影響相處品質"),
    "high-attraction-high-friction": ("高吸引高摩擦型", "吸引很明顯，但靠近後也容易碰到彼此的敏感點"),
    "natural-attraction": ("自然吸引型", "好感比較容易自然出現，後續仍要看雙方會不會繼續靠近"),
    "slow-safety": ("慢熱安全感型", "關係需要可預期的小互動，信任才會逐漸建立"),
}

DYNAMIC_MEANINGS = {
    "unknown": "目前沒有足夠線索指出哪一種相處問題最關鍵",
    "communication-repair": "你們最容易卡在話怎麼說，說得越急，越可能聽不到彼此真正的意思",
    "outer-intensity": "感受可能很強，但還要看對方有沒有連續而清楚的行動",
    "identity-rhythm": "彼此都很在意有沒有被看見，一受傷就容易先顧著保護自尊",
    "emotional-safety": "兩個人都會留意對方的冷熱，安全感不足時，小反應也容易被放大",
    "saturn-pressure": "話題一碰到責任、承諾或距離，關係就容易變得拘謹",
    "action-conflict": "一方想快點處理時，另一方的反應也容易變硬，最後變成互相頂住",
    "attraction-pursuit": "靠近時很有火花，但熱度之後是否還有持續行動更重要",
    "jupiter-support": "彼此有鼓勵和支持的條件，重點是好意能不能變成實際幫助",
    "slow-safety": "你們需要先累積幾次可預期的互動，才比較容易放心靠近",
}

FIT_INTERACTIONS = {
    "unknown": "目前先保留沒有被星盤線索清楚支持的部分",
    "communication-repair": "平常可以聊得來，但重要話題一變急，就容易各自解釋、沒有真正聽完",
    "outer-intensity": "靠近時很難完全無感，拉開距離後也容易反覆想起對方",
    "identity-rhythm": "相處順時會互相肯定，受傷時也容易把沉默聽成不被重視",
    "emotional-safety": "氣氛好的時候很親近，一出現冷淡就容易開始猜對方是不是變了",
    "saturn-pressure": "輕鬆相處時不一定有問題，一談未來或責任就容易有人慢下來",
    "action-conflict": "兩個人都有反應時很有火花，但意見不同也容易很快升高音量",
    "attraction-pursuit": "曖昧和熱絡可以很自然，真正困難的是熱度過後仍願不願意留下來",
    "slow-safety": "互動需要累積，忽然加快關係進度反而容易讓其中一方退開",
}

ARCHETYPE_SITUATIONAL = {
    "unknown": "線索還不足時，先分開看吸引、摩擦和實際選擇，不急著用類型替關係定案",
    "past-life-intensity": "靠近或分開時都容易留下強烈感受，但回到日常後仍要看雙方是否持續行動",
    "growth-support": "彼此鼓勵時很容易看見可能性，真正考驗是好意能不能變成時間和實際幫助",
    "communication-repair": "平常可能聊得來，重要話題一變急，就會看出彼此能不能把誤會說開",
    "mutual-activation": "一個人的冷熱很快會影響另一個人，因此小反應也可能改變整體氣氛",
    "emotional-familiarity": "相處順時很容易感到熟悉，一方不安時，另一方的情緒也容易跟著被帶動",
    "growth-through-friction": "日常沒有壓力時不一定有問題，碰到責任和差異時才看得出能不能一起調整",
    "fast-spark-conflict": "互動熱起來很快，意見不同時升高速度也快，停不停得下來會決定相處品質",
    "high-attraction-high-friction": "好感明顯時很容易靠近，但越在意也越容易碰到彼此敏感和防備的地方",
    "natural-attraction": "輕鬆相處時好感容易自然出現，後續要看這份靠近會不會變成持續選擇",
    "slow-safety": "互動規律而可預期時信任會慢慢增加，突然加快則容易讓其中一方退回原位",
}

ARCHETYPE_RELATIONAL = {
    "unknown": "目前沒有足夠證據把你們放進固定類型，關係結果仍要由後續互動慢慢說明",
    "past-life-intensity": "你們越被彼此牽動，越需要把強烈感受和能不能長期相處分開看",
    "growth-support": "你們容易看見彼此可以變得更好的地方，但只有雙方都投入，支持才不會變成空泛期待",
    "communication-repair": "你們能不能走穩，很大部分取決於誤會出現後是否還能聽完並重新說清楚",
    "mutual-activation": "你們會放大彼此的反應，一個人先退或先靠近，另一個人通常也很快跟著改變",
    "emotional-familiarity": "你們很容易碰到彼此的情緒，所以靠近會有熟悉感，不安也會比一般關係更有感",
    "growth-through-friction": "你們的差異會反覆要求雙方調整；只有一個人忍耐，關係很容易回到原本問題",
    "fast-spark-conflict": "你們靠近和爭執都很快，誰能先讓速度降下來，會決定火花最後變親近還是對抗",
    "high-attraction-high-friction": "你們不缺吸引，但越想靠近越容易碰到敏感點，穩定需要兩邊都改變回應方式",
    "natural-attraction": "你們容易自然欣賞彼此，能不能走遠則要看好感之後是否仍願意持續投入",
    "slow-safety": "你們需要用可預期的小互動累積信任，任何一方急著加速，都可能讓另一方先退開",
}

ARCHETYPE_FORMS = {
    key: RealizationForms(value[1], ARCHETYPE_SITUATIONAL[key], ARCHETYPE_RELATIONAL[key])
    for key, value in ARCHETYPES.items()
}

DYNAMIC_SITUATIONAL = {
    "unknown": "目前還看不出哪一個相處問題最常主導你們的反應",
    **FIT_INTERACTIONS,
    "jupiter-support": "談可能性時彼此容易互相鼓勵，回到日常後要看支持是否真的被完成",
}

DYNAMIC_RELATIONAL = {
    "unknown": "目前先保留沒有被清楚支持的部分，不用一個泛稱替你們的相處下結論",
    "communication-repair": "你越急著補充，他越可能只聽見壓力，最後兩個人說了很多卻沒有回答同一件事",
    "outer-intensity": "你們越被強烈感受吸引，越容易用猜測補上空白；真正差別仍在後續有沒有連續行動",
    "identity-rhythm": "一個人覺得不被重視時會先保護自尊，另一個人的沉默也因此更容易被聽成否定",
    "emotional-safety": "一個人的冷熱會放大另一個人的不安，安全感不足時，一次冷淡或沉默就容易被理解成關係出了問題",
    "saturn-pressure": "一個人越要求承諾，另一個人越先考慮責任和距離，回應因此容易慢下來",
    "action-conflict": "一個人越急著處理，另一個人的反應越容易變硬，最後兩邊都進入對抗",
    "attraction-pursuit": "一方越用熱度確認關係，另一方越可能只回應當下，後續行動才能說明熱度會不會留下",
    "jupiter-support": "你們容易互相鼓勵，但如果沒有實際投入，好意會停在期待，無法真正支撐關係",
    "slow-safety": "一方越急著拉近距離，另一方越需要退回安全位置；穩定只能靠可預期互動累積",
}

DYNAMIC_FORMS = {
    key: RealizationForms(DYNAMIC_MEANINGS[key], DYNAMIC_SITUATIONAL[key], DYNAMIC_RELATIONAL[key])
    for key in DYNAMIC_MEANINGS
}

FIT_DYNAMIC_SUFFIXES = (
    "後續要看雙方能不能換一種回應方式",
    "同樣的問題有沒有改變，比一時氣氛更重要",
    "相同情況如果一直重複，兩個人都會很累",
    "真正的差別在於彼此是否願意一起調整",
    "需要用幾次連續互動確認是否真的改善",
    "只有一個人改變，很容易又回到原本的相處方式",
    "兩邊都能看見問題時，關係才有機會慢慢鬆開",
    "不能只看順利的時候，也要看衝突出現後怎麼處理",
    "這會直接影響關係能不能從有感覺走到有共識",
    "比起誰比較用心，更需要看兩個人的做法能不能配合",
)

FIT_INTERACTION_SUFFIXES = (
    "這也是靠近後最容易重複的情況",
    "如果沒有人先調整，類似問題還會再出現",
    "相處時間一拉長，這個差異會更明顯",
    "壓力變高時，兩個人最容易回到這個模式",
    "感情好的時候不明顯，遇到分歧就容易被放大",
    "這個地方能不能改善，會決定相處是否越來越累",
    "雙方都願意停一下，才不會讓反應互相推高",
    "看懂這個模式後，下一次才有機會換一種處理方式",
    "真正需要磨合的不是好感，而是出現壓力時的反應",
    "這種差異不是不能調整，但需要兩個人都參與",
)

FIT_SIGNAL_SUFFIXES = {
    "attraction": (
        "所以彼此的注意通常不難被感受到",
        "這會讓靠近的第一步顯得很自然",
        "相處順利時，好感很容易從反應裡看出來",
        "因此你們之間通常不缺少想靠近的理由",
        "這份吸引會讓彼此很快注意到對方的變化",
        "互動剛開始時，關係容易有明顯火花",
        "這讓輕鬆聊天或自然關心比較容易發生",
        "彼此有感覺時，通常不需要太多鋪陳",
        "這份好感比較容易出現在日常的小反應裡",
        "你們會自然留意對方有沒有回應自己的靠近",
    ),
    "friction": (
        "壓力一高，這個差異就容易變成誤會",
        "如果急著分對錯，原本的問題會更難說清楚",
        "兩個人情緒都上來時，這裡最容易卡住",
        "同樣的情況反覆出現，會讓彼此越來越防備",
        "這也是靠近後需要特別調整的地方",
        "沒有先停下來時，反應很容易一個推高一個",
        "真正難處理的不是意見不同，而是當下的回應方式",
        "只靠其中一方忍耐，很難讓這個問題真正消失",
        "彼此都想保護自己時，原本的小事會變得更大",
        "這個差異需要被說清楚，不能只等氣氛自己變好",
    ),
    "growth": (
        "先從這個改變開始，會比一次重談整段關係有效",
        "這件事做得到，才有可能慢慢累積新的信任",
        "小而持續的改變，比一時保證更能看出修復能力",
        "如果雙方都願意做到，原本的摩擦會比較容易下降",
        "這是目前最實際、也最容易驗證的調整方向",
        "先看這一步能不能維持，再決定是否談更大的問題",
        "能把這件事做好，才表示相處方式真的開始改變",
        "這個方向需要雙方一起做，不能只靠一個人努力",
        "把改變放進日常，會比反覆確認感情更有用",
        "先累積幾次新的經驗，關係才不會立刻回到原點",
    ),
}

FIT_CAUTIONS = (
    "這個類型說明你們容易怎麼相處，不能直接當成承諾或復合答案",
    "有吸引和有機會長久是兩件事，後者仍要看雙方的實際選擇",
    "合盤可以指出相處模式，不能替任何一方決定要不要繼續",
    "關係名稱不是結果，真正重要的是相同問題能不能逐漸改善",
    "再強的吸引也需要後續行動，不能只用感覺判定未來",
    "相處有火花不代表沒有風險，仍要看衝突後能不能修復",
    "星盤能解釋彼此為何互相牽動，不能保證關係一定走向哪裡",
    "類型相同的兩段關係，也會因為成熟度和選擇有不同結果",
    "不要因為名稱聽起來特別，就忽略已經出現的現實問題",
    "關係是否值得繼續，最後仍要看尊重、責任和持續行動",
    "這些線索適合用來理解相處，不適合拿來替對方做決定",
    "知道可以怎麼調整，不代表關係自然會變好，仍要看兩個人是否一起改變",
    "不要只看彼此有沒有感覺，也要看相處是否保有尊重",
    "類型能幫你理解問題，不能取代一段時間的現實觀察",
    "一個明顯優點不能抵銷反覆受傷，需要把兩邊一起看",
    "彼此牽動很深時，更要分清楚吸引、習慣和願不願意經營",
    "修復潛力需要行動證明，不能只停在知道問題在哪裡",
    "關係能否走穩，取決於兩個人是否願意改變同樣的相處問題",
    "不要用合盤名稱要求自己留下，也不要用它替對方承諾",
    "看見相處優勢的同時，也要誠實面對一直沒有改善的部分",
)

FIT_HEADLINE_SUFFIXES = (
    "火花之外還要看後續",
    "好感和磨合需要一起看",
    "靠近容易，走穩需要調整",
    "相處關鍵在衝突後怎麼做",
    "吸引明顯，也要照顧彼此界線",
    "真正考驗在關係變重之後",
    "有感覺，更需要新的相處方法",
    "相同問題能否改善最重要",
    "日常行動會決定關係方向",
    "彼此都調整才不會回到原點",
    "安全感要靠連續互動累積",
    "理解差異後還需要實際改變",
)

ATTRACTION_PAIRS = {
    "sun-moon": "你們很容易注意到彼此的情緒和反應",
    "sun-venus": "欣賞和好感通常來得自然，也容易看到對方可愛的地方",
    "sun-mars": "靠近時火花和行動感來得很快",
    "venus-mars": "彼此的吸引力明顯，曖昧氣氛也容易升溫",
    "moon-venus": "相處時容易產生溫柔、熟悉和被照顧的感覺",
    "moon-moon": "兩個人的情緒節奏容易互相感應",
    "venus-venus": "你們喜歡的相處方式比較容易對上",
}

FRICTION_PAIRS = {
    "mercury-mars": "一談急事，說話速度容易變快，口氣也會跟著變硬",
    "mercury-moon": "一方想把話說清楚，另一方先感受到口氣，容易各自卡在不同重點",
    "mercury-sun": "說法碰到自我認同時，容易把意見不同聽成否定",
    "mercury-venus": "一方重視把話說清楚，另一方更在意口氣和感受，容易錯過彼此好意",
    "mercury-saturn": "重要話題容易怕說錯，有人會沉默、保留或反覆確認",
    "mercury-mercury": "同一句話可能有不同理解，越急著解釋越容易錯開重點",
    "mars-mars": "兩個人都想按自己的速度處理，意見不同時容易正面頂住",
    "mars-saturn": "一個人想往前，另一個人想先停下確認，久了會互相誤解",
    "moon-mars": "情緒一被碰到，反應容易比原本的事情更大",
    "moon-moon": "兩人的情緒節奏不同時，一個想靠近，另一個可能先退開",
    "moon-venus": "一方期待被照顧的方式，可能不是另一方自然表達好感的方式",
    "moon-saturn": "需要安慰時，另一方可能先沉默、講道理或拉開距離",
    "venus-mars": "一方想靠近的方式，可能讓另一方感到太快或太直接",
    "venus-venus": "兩個人表達喜歡的方式不同，容易各自付出卻沒有收到",
    "venus-saturn": "好感一碰到承諾或距離，表達就容易變得保守",
    "sun-saturn": "談到責任時，有人容易覺得自己做得不夠好或受到限制",
    "sun-moon": "一個人的做法可能碰到另一個人的情緒需要",
    "sun-venus": "表達好感的方式不同時，一方的用心可能沒有被另一方收到",
    "sun-mars": "一方想主導方向時，另一方容易用行動或脾氣回應",
    "outer-planet-intensity": "感覺很強時也容易猜測、理想化，或把沉默想得太多",
}

GROWTH_PAIRS = {
    "mars-saturn": "先說清楚彼此能接受的速度，再決定眼前一件做得到的事",
    "moon-saturn": "把安慰方式說具體，讓需要空間和需要陪伴都能被理解",
    "sun-saturn": "把責任拆成小安排，會比一次要求完整承諾更容易做到",
    "venus-saturn": "穩定的小行動比反覆確認感情更能累積信任",
    "mercury-saturn": "重要話題先約好時間和範圍，會比較容易把話說完",
}

OBSERVABLE_COPY = {
    "partner-continues-without-prompt": "你沒有追問時，他仍主動把話題接下去，才算出現新的變化",
    "reply-only-after-user-prompt": "如果回應只在你主動後短暫出現，就還不能算持續靠近",
    "short-specific-message-is-easier": "只談一件具體小事時，他的回應變得自然，才算互動有所改善",
    "long-explanation-shrinks-reply": "訊息一變長，他就回得更慢或更短，表示現在不適合談太多",
    "small-concrete-topic-lowers-defense": "話題縮小後，他不再立刻防備，才算相處方式有所改變",
    "commitment-topic-shrinks-reply": "一談承諾或定位，他就延後或縮短回應，表示壓力仍然存在",
    "smaller-action-lowers-conflict": "一次只處理一件事時，你們比較少爭辯，才算舊問題開始改變",
    "confrontation-hardens-tone": "一攤牌或測試反應，口氣就很快變硬，表示現在不適合逼問",
    "intensity-has-continuous-action": "強烈感受過後仍有連續而清楚的行動，才算真正的改變",
    "interaction-relies-on-guessing": "如果互動仍靠猜測、回憶或氣氛維持，就還沒有新的事實",
    "permitted-channel-respected": "他主動恢復聯絡，而且願意持續對話，才算出現新的變化",
    "unforced-channel-appears": "你停下來後，他仍會主動開口，才表示沉默開始鬆動",
    "partner-initiates-continuation": "這次話題告一段落後，他仍會主動開啟下一次對話，才表示他也想維持聯絡",
    "shared-space-stays-civil": "不談感情時仍能自然相處，才表示共同場合的壓力正在下降",
    "spontaneous-next-interaction": "這次互動結束後，他仍會主動開啟下一次對話，才算出現新的變化",
}

OBSERVABLE_SITUATIONAL = {
    "partner-continues-without-prompt": "你沒有再追問時，他仍會自己把同一個話題接下去",
    "reply-only-after-user-prompt": "只有你先開口時才短暫出現回應，之後又回到原本的安靜",
    "short-specific-message-is-easier": "內容只剩一件具體小事時，他的回應會比較完整而自然",
    "long-explanation-shrinks-reply": "訊息越長、解釋越多時，他的回覆會跟著變慢或變短",
    "small-concrete-topic-lowers-defense": "話題縮到一件能回答的小事後，他的口氣不再那麼緊",
    "commitment-topic-shrinks-reply": "話題一碰到承諾或定位，他就立刻延後、縮短或避開回答",
    "smaller-action-lowers-conflict": "一次只處理一件事時，你們能把話說完，不再很快變成爭辯",
    "confrontation-hardens-tone": "一攤牌或測試他的反應，對話就很快從說明變成互相防備",
    "intensity-has-continuous-action": "強烈感受過後，他仍有連續而清楚的行動留在日常裡",
    "interaction-relies-on-guessing": "沒有新的行動時，這段互動主要靠回憶、氣氛或猜測維持",
    "permitted-channel-respected": "他如果想恢復互動，會自己重新打開原本允許的聯絡方式",
    "unforced-channel-appears": "你沒有繼續推動時，他仍會主動開口，而不是回到完全沉默",
    "partner-initiates-continuation": "聊天告一段落後，他仍會主動開啟下一次對話",
    "shared-space-stays-civil": "共同場合不談感情時，你們仍能自然相處並維持基本禮貌",
    "spontaneous-next-interaction": "這次互動自然結束後，他還會在你沒有追問時再次開口",
}

OBSERVABLE_RELATIONAL = {
    "partner-continues-without-prompt": "你不再追問後，他仍願意主動接著聊，才表示不只是禮貌回覆",
    "reply-only-after-user-prompt": "如果互動一直只在你推動後短暫出現，關係目前仍主要靠你維持",
    "short-specific-message-is-easier": "內容短而具體時他才比較願意回應，表示現在只適合簡單對話",
    "long-explanation-shrinks-reply": "你越想一次解釋完整，他的回應越短，表示重要問題需要分開談",
    "small-concrete-topic-lowers-defense": "你把話題縮小後他也能放鬆，表示改變互動方式確實有助於減少防備",
    "commitment-topic-shrinks-reply": "你一談承諾他就退開，代表關係目前還無法承受定位和結果壓力",
    "smaller-action-lowers-conflict": "你們把問題拆小後能少一點爭辯，表示原本卡住的不只內容，也包括處理速度",
    "confrontation-hardens-tone": "你越用攤牌確認答案，他越先保護自己，這種反應表示逼問仍會放大原本問題",
    "intensity-has-continuous-action": "感受很強之後仍有穩定行動，才表示兩個人真的願意經營",
    "interaction-relies-on-guessing": "沒有新行動卻一直靠猜測維持希望，表示關係現況和你的期待仍有距離",
    "permitted-channel-respected": "他願意自己恢復原本聯絡方式，才表示界線真的由他主動改變",
    "unforced-channel-appears": "你停下來後他仍主動開口，才表示聯絡不只靠你一個人維持",
    "partner-initiates-continuation": "這次話題告一段落後，他仍主動開啟下一次對話，才表示他也想維持聯絡",
    "shared-space-stays-civil": "你不把共同場合變成關係壓力後，雙方仍能自然相處，才表示日常安全感開始恢復",
    "spontaneous-next-interaction": "一次互動結束後仍有下一次自然靠近，才表示關係沒有只停在當下氣氛",
}

OBSERVABLE_FORMS = {
    key: RealizationForms(value, OBSERVABLE_SITUATIONAL[key], OBSERVABLE_RELATIONAL[key])
    for key, value in OBSERVABLE_COPY.items()
}

ACTION_MODE_COPY = {
    "boundary-only": ("先尊重已經關上的聯絡界線", "目前不要主動聯絡，也不要改用其他帳號或請朋友代傳"),
    "observe-or-single-low-stimulation-test": ("先觀察，不急著測試關係", "如果原本仍能聯絡，只保留一次簡短而沒有要求的訊息"),
    "shared-space-boundary": ("先讓共同場合保持自然", "只處理工作或日常需要，不把共同場合變成談判關係的地方"),
    "small-bid-response-led": ("用一次簡短互動看他的反應", "只開一個容易回答的小話題，之後由他的回應決定要不要繼續"),
    "tone-repair-in-existing-channel": ("先修正說話方式，不急著談結果", "在原本的聯絡裡只澄清一件事，避免把整段關係一次攤開"),
}

REPAIR_COPY = {
    "unknown": "先不要假設只有一種做法能改善關係，從眼前最明確的問題開始",
    "communication-repair": "把訊息縮短，只談現在最需要釐清的一件事",
    "outer-intensity": "先看現實裡有沒有持續行動，不用強烈感受替空白補答案",
    "identity-rhythm": "先說明具體事件，不用一句話評價對方整個人",
    "emotional-safety": "先讓彼此知道什麼說法會受傷，以及怎樣回應比較有幫助",
    "saturn-pressure": "把責任題拆開，先確認一件雙方都做得到的安排",
    "action-conflict": "口氣開始變硬時先停，不在情緒升高時繼續追答案",
    "attraction-pursuit": "先讓好感留在自然互動裡，不急著把熱度變成關係結論",
    "jupiter-support": "把鼓勵變成一件真的做得到的支持，不只停在好聽的期待",
    "slow-safety": "先累積幾次可預期的小互動，再決定要不要增加靠近的程度",
}

ACTION_REPAIR_VARIANTS = {
    "unknown": (
        "先處理眼前最明確的一件事，不替還不清楚的原因補答案",
        "先從你能確認的問題開始，不急著替整段關係找單一原因",
        "目前不要套用固定方法，先看哪一件事真的影響你們相處",
        "把沒有證據的推測放下，只回應這次實際發生的事情",
        "先選一個看得見的問題調整，不把猜測當成對方的想法",
        "沒有明確線索時，先用最簡單而尊重界線的方式處理",
    ),
    "communication-repair": (
        "把訊息縮短，只談現在最需要釐清的一件事",
        "先選一件最需要說清楚的事，不要同時補上所有委屈",
        "把最重要的話留成一句，等對方回應後再決定要不要多說",
        "這次只澄清一個誤會，不把其他問題一起帶進來",
        "先問一個容易回答的問題，讓對話能從小地方重新開始",
        "把想說的內容減到一個重點，說完先停在那裡",
    ),
    "outer-intensity": (
        "先看他接下來有沒有連續行動，不用強烈感受替空白補答案",
        "把判斷放在他實際做了什麼，不用一時靠近猜完整答案",
        "先記錄幾次真實互動，再分辨這是短暫熱度還是願意經營",
        "感覺很強時先不要急著下結論，等後續行動自己說明",
        "先看熱絡之後他有沒有繼續靠近，不只看當下氣氛",
        "把注意力放回看得見的回應，不用猜測補上沒有發生的部分",
    ),
    "identity-rhythm": (
        "先說明具體發生的事，不用一句話評價對方整個人",
        "把批評換成一件看得見的行為，讓對方知道你真正介意什麼",
        "這次只談哪個做法讓你受傷，不把問題說成他整個人都不好",
        "先描述事情怎麼發生，再說你的感受，不急著判斷誰對誰錯",
        "拿掉責怪人的字眼，只留下需要一起處理的那件事",
        "把對人的否定換成具體請求，才比較容易聽見彼此",
    ),
    "emotional-safety": (
        "先說清楚哪種口氣會讓你受傷，也告訴他怎麼回應比較有幫助",
        "情緒還很滿時先停一下，等兩個人都能聽完再繼續",
        "先讓彼此知道談不下去時可以暫停，不必當場逼出答案",
        "把需要說得具體，例如先聽完或晚點再回，不要讓對方靠猜",
        "先降低責怪和質問，讓真正介意的事有機會被聽見",
        "在談內容以前先調整口氣，避免彼此一開口就想保護自己",
    ),
    "saturn-pressure": (
        "把責任問題拆開，先確認一件雙方都做得到的安排",
        "不要一次談完整未來，先約定眼前能不能完成一件小事",
        "先把承諾換成具體安排，例如時間、做法和誰來完成",
        "話題碰到責任時先縮小範圍，只談最近需要處理的一件事",
        "把長期答案留到後面，先看一個小約定能不能真的做到",
        "先確認彼此目前能負責到哪裡，不要求當場承諾全部",
    ),
    "action-conflict": (
        "口氣開始變硬時先停，不在情緒升高時繼續追答案",
        "兩個人都急著回應時先暫停，等能聽完一句話再談",
        "發現話題變成互相反駁時，就先結束這次對話",
        "先把說話速度放慢，不在彼此都生氣時決定關係方向",
        "一方開始提高音量或重複立場時，就把剩下的話留到下次",
        "先離開當下的爭辯，等口氣平穩後只處理最初那件事",
    ),
    "attraction-pursuit": (
        "先讓好感留在自然互動裡，不急著把熱度變成關係結論",
        "靠近順利時也先保持原來速度，看他之後會不會主動延續",
        "不要因為一時熱絡就追問關係要不要往前，先看下一次互動是否自然出現",
        "先享受能正常相處的部分，不急著要求對方立刻定義關係",
        "把熱度和承諾分開看，等連續行動出現後再判斷",
        "先看好感能不能落到日常，不用一次談到完整未來",
    ),
    "jupiter-support": (
        "把鼓勵變成一件真的做得到的支持，不只停在好聽的期待",
        "先完成一件答應過的幫助，讓支持不只留在口頭",
        "把想一起變好的期待落到最近能完成的一個安排",
        "先看彼此是否願意實際投入時間，而不是只談可能性",
        "用一件具體支持確認好意能不能進入日常",
        "把共同期待拆成現在能做到的第一步，做完再談更遠",
    ),
    "slow-safety": (
        "先累積幾次可預期的小互動，再決定要不要增加靠近的程度",
        "維持固定而不施壓的節奏，讓信任有時間慢慢形成",
        "先讓每一次回應都能自然結束，不急著把關係往前推",
        "用幾次穩定的小行動確認安全感，不靠一次熱絡下結論",
        "先保持容易做到的互動頻率，等雙方都放鬆再增加內容",
        "讓靠近變得可預期，沒有穩定以前不增加新的要求",
    ),
}

BLOCKED_ACTION_COPY = {
    "alternate-account-contact": "換帳號聯絡",
    "asking-for-answer-now": "要求現在就回答",
    "emotional-confrontation": "在情緒很滿時攤牌",
    "forcing-relationship-definition": "逼對方立刻定義關係",
    "long-explanation": "傳很長的解釋",
    "long-pressure-message": "用長訊息施壓",
    "public-confrontation": "在公開或共同場合談判",
    "rapid-escalation": "短時間內連續加重話題",
    "relationship-definition-push": "追問關係定位",
    "repeated-messages": "對方沒回時繼續補訊息",
    "testing-loyalty": "用試探確認忠誠",
    "third-party-pressure": "請朋友代為施壓",
    "turning-reply-into-commitment": "把一次回覆當成承諾",
    "using-shared-space-as-pressure": "利用共同場合逼對方談關係",
}

CHART_HEADLINES = (
    "你和他的親密關係習慣",
    "兩個人怎麼尋找安全感",
    "你們各自怎麼面對重要關係",
    "先認識彼此的情感習慣",
    "你需要什麼，他又怎麼反應",
    "兩個人的安心方式不太一樣",
    "你怎麼確認愛，他怎麼處理壓力",
    "先分清楚彼此原本的反應習慣",
    "你在意的事，和他的保護方式",
    "兩個人各自需要怎樣的回應",
    "你們在關係裡最自然的樣子",
    "看懂彼此靠近和退開的習慣",
    "兩個人在感情裡各自重視什麼",
    "你怎麼表達，他怎麼保護自己",
    "彼此的需要和反應從哪裡開始",
    "你們各自習慣用什麼方式安心",
    "重要關係裡最自然的反應習慣",
    "先把兩個人的情感需要分開看",
    "你在關係裡的需要，他的壓力反應",
    "理解彼此原本的親密關係節奏",
)

CHART_NEED_SUFFIXES = (
    "這也是你確認一段關係是否可靠的重要方式",
    "只靠一句保證，通常不足以讓你真正放心",
    "當回應不明確時，你心裡會很快出現疑問",
    "你會用一段時間的相處，而不是一時熱情做決定",
    "對方有沒有持續做到，會比當下說得多好聽更重要",
    "一旦這部分不穩，你就容易反覆確認對方的態度",
    "你真正需要的是可以慢慢相信的日常感受",
    "看見前後一致的行動，你才會逐漸放下戒心",
    "關係裡有沒有清楚回應，會直接影響你的安心程度",
    "你不是只想聽答案，也需要看到答案如何落在生活裡",
)

CHART_COMMUNICATION_SUFFIXES = (
    "你希望對方先聽懂重點，再一起處理分歧",
    "話沒有被聽懂時，你會想再補充更多細節",
    "只要對話還有來回，你就比較能整理自己的感受",
    "你不怕談問題，更怕兩個人一直說不到同一件事",
    "對方願意認真回應時，你也比較能放下原本的防備",
    "重要話題若被打斷，你心裡通常還會一直掛著",
    "你需要的不只是說完，而是確認對方真的理解",
    "談話有清楚結論時，你會比只有安撫更容易安心",
    "你會從對方怎麼回話，感受這段關係有沒有被重視",
    "能不能好好談完，對你來說本身就是親密的一部分",
)

CHART_PRESSURE_SUFFIXES = (
    "所以他的第一句話不一定是最後的想法",
    "他通常要先從壓力裡退開，才說得出真正的感受",
    "當下要求他解釋清楚，容易只得到更簡短的回應",
    "他越覺得自己被檢查，越難自然說出心裡的話",
    "這時先停一下，通常比繼續追問更容易恢復對話",
    "他的沉默有時是在整理自己，不代表事情已經有答案",
    "先讓他知道不必立刻表態，對話才比較可能繼續",
    "如果壓力沒有下降，他會先處理自保，而不是處理關係",
    "等口氣和情緒都放鬆，他才比較能回到原本的問題",
    "他需要先確定談話不會變成責怪，才願意多說一些",
)

CHART_ACTION_FOLLOWUPS = (
    "一次只談一件事，說完先讓他回應",
    "確認他還聽得進去，再決定要不要繼續",
    "如果口氣開始變重，就把剩下的話留到下次",
    "先處理眼前發生的事，不要同時追究整段關係",
    "問完一個問題就停，讓他有時間整理自己的答案",
    "先確認彼此理解相同，再往下一個話題走",
    "把最重要的那句話說清楚，其餘內容可以晚一點再談",
    "他開始重複立場時，不要用更多理由逼他改口",
    "這次只處理具體事件，不把愛不愛一起放進來問",
    "讓談話有結束點，會比一次說完所有委屈更有幫助",
    "先看他對這件事的回應，再決定下一次要談多深",
    "雙方都能平靜聽完時，再處理需要更多時間的部分",
)

CHART_CAUTIONS = (
    "這些是習慣，不代表誰愛得比較多，也不能代替兩個人的選擇",
    "反應方式可以解釋差異，不能直接拿來判定一個人的心意",
    "星盤描述的是常見反應，不是對這段關係結果的判決",
    "需要確認和需要空間都只是習慣，不等於其中一方比較不在乎",
    "一個人回得快或慢，不能單獨證明他對關係有多認真",
    "看懂習慣能幫助你減少誤會，但傷人的做法仍需要被正視",
    "這些傾向會隨成熟度和現實選擇改變，不是固定命運",
    "個人星盤能說明需求，不能保證兩個人一定適合或不適合",
    "相處方式不同不代表沒有感情，仍要看雙方願不願意調整",
    "安全感來源不同時容易誤解，但責任仍在每個人的實際行動",
    "不要用一個反應習慣替對方的所有行為下定論",
    "理解彼此的底色之後，還是要回到當下真實發生的事情",
    "習慣只能解釋第一反應，後續怎麼選擇仍由每個人負責",
    "一時退開可能和壓力有關，但長期忽略仍需要被正視",
    "知道彼此需要什麼，不代表你必須放棄自己的基本界線",
    "個性差異可以磨合，反覆不尊重則不能只用個性解釋",
    "理解他的保護方式，不等於所有沉默都應該由你等待",
    "你的安全感需要被重視，也要用現實行動確認是否被回應",
    "反應習慣不是藉口，雙方仍要為說過的話和做法負責",
    "星盤提供理解角度，關係品質仍取決於長期相處和選擇",
)

CORE_PARTNER_SUFFIXES = (
    "這會影響他願不願意把話繼續說下去",
    "如果壓力太高，他會先照顧自己的防備",
    "他感覺被理解時，才比較可能說出真正想法",
    "要求越急，他越容易先縮短回應",
    "理解這個反應，不代表需要接受任何傷人的做法",
    "他的後續行動仍然要由現實互動來確認",
    "先用他能理解的方式開口，才看得到真實反應",
    "當這個需要被忽略時，他通常不會立刻說明原因",
    "給他適當空間，不等於你必須無限等待",
    "理解他的需要之後，仍要保留你自己的界線",
)

CORE_OBSERVABLE_SUFFIXES = (
    "連續出現幾次，才比較能說明互動真的變了",
    "只發生一次時先保留，不急著把它當成答案",
    "如果總是需要你先推動，代表關係還沒有真正往前",
    "觀察一段時間，比當下追問原因更容易看清楚",
    "真正的改變會自然重複，不需要每次都由你提醒",
    "把注意力放在行動是否持續，會比猜測心意可靠",
    "對方願意主動完成下一步時，這個訊號才更有份量",
    "如果後續又回到原樣，就不要只記住短暫的好轉",
    "先看回應能不能延續，再決定要不要花更多心力",
    "這能幫你分清楚一時氣氛和真正的關係變化",
    "沒有新的行動時，先不要用過去的感情補上答案",
    "讓幾次現實互動累積起來，再判斷是否值得繼續",
)

TIMING_CONTACT_SUFFIXES = (
    "現有狀態就是目前的行動上限",
    "現在的回應方式比挑選日期更重要",
    "等界線有改變，再考慮下一步",
    "不要讓想聯絡的焦急蓋過眼前事實",
    "對方目前願意接受多少互動，需要先被尊重",
    "用已經發生的反應決定靠近程度",
    "時機再好，也不能跳過目前的聯絡狀態",
    "能不能自然說上話，是目前最實際的起點",
    "雙方都願意說話以後，再談日期",
    "讓現實狀態決定速度，不用急著創造機會",
)

TIMING_ACTION_SUFFIXES = (
    "做完這一步就先停，讓對方決定是否回應",
    "不用同時談感情和未來，先留下一個容易結束的話題",
    "保持簡短，才能看出對方原本願不願意回應",
    "這次不求完整答案，只看交流能不能保持自然",
    "不要連續補充，讓這次互動有清楚的結束點",
    "先把壓力降下來，再看關係有沒有新的變化",
    "對方沒有延續時，不需要立刻再找第二個機會",
    "一次行動就足夠，後續交給真實反應說明",
    "先確認氣氛沒有變硬，再處理更重要的問題",
    "這一步的目的只是看互動是否順暢，不是取得承諾",
    "讓訊息本身容易回答，也允許對方暫時不回",
    "先觀察幾天的實際變化，不用在同一天完成所有事",
    "把想問的內容減到一個問題，對方才容易自由選擇回不回",
    "先避免關係定位，讓這次交流只停在日常範圍",
    "如果對話自然結束，不需要立刻找新的理由重新開口",
    "完成一次簡單互動後，至少等到對方自己有所動作",
    "先確認回應沒有變得更冷，再考慮增加下一步",
    "不要用補充說明延長話題，讓交流保持原本的輕度",
    "這次只確認彼此能否正常說話，不處理感情結論",
    "若對方只禮貌回答，就讓話題自然停在那裡",
)

TIMING_CAUTIONS = (
    "時段只能提示氣氛，不能保證聯絡、復合或對方的決定",
    "日期可以幫你調整做法，對方仍會按自己的意願回應",
    "即使氣氛較柔和，也要以對方當下的界線和行動為準",
    "沒有實際回應時，不要只因一個時段看起來較好就增加聯絡",
    "較順的時段不等於對方已經準備好談關係",
    "時機只能改變談話氣氛，不能替代雙方的真實意願",
    "不要為了等某個日期，忽略關係長期沒有進展的事實",
    "如果對方已明確拒絕聯絡，任何時段都不適合跨過界線",
    "氣氛變輕只能當成一個參考，不能直接當成感情答案",
    "日子看起來適合，也要讓訊息保持簡短而沒有要求",
    "真正重要的不是哪一天，而是對方是否願意自然回應",
    "時機資料不足時，保守一點比勉強找出答案更可靠",
    "不要把短期氣氛變好，直接解讀成長期關係已經改變",
    "對方若不願意回應，等待較好的時段也不會自動改變現況",
    "時段只能幫你決定要快一點還是慢一點，不能預測他會怎麼做",
    "真正的修復仍需要雙方參與，日期本身不會解決舊問題",
    "選擇聯絡以前，先確認這個動作不會跨過已經說明的界線",
    "如果你正處在很焦急的狀態，先等自己平靜比挑日期更重要",
    "可以參考互動氣氛，但不要因此忽略長期反覆出現的問題",
    "沒有可靠時段時，維持現有界線就是較穩妥的做法",
)

TIMING_WINDOW_TEMPLATES = (
    "{period}左右，{meaning}",
    "到了{period}前後，{meaning}",
    "{period}這段時間，{meaning}",
    "可以留意{period}前後，{meaning}",
    "{period}附近的氣氛可能有變化，{meaning}",
    "若要觀察互動，可留意{period}前後，{meaning}",
    "從{period}附近的反應來看，{meaning}",
    "{period}可以當成觀察點，{meaning}",
    "互動到了{period}前後，{meaning}",
    "在{period}這個區間，{meaning}",
    "可把{period}前後當作參考，{meaning}",
    "來到{period}附近時，{meaning}",
    "若觀察{period}這段時間，{meaning}",
    "{period}前後值得留意，{meaning}",
    "互動在{period}附近可能稍有變化，{meaning}",
    "想看氣氛是否改變，可以留意{period}，{meaning}",
    "以{period}作為短期觀察區間時，{meaning}",
    "{period}附近只適合當參考，{meaning}",
    "到了{period}這個階段，{meaning}",
    "短期可以留意{period}前後，{meaning}",
)

ACTION_SENTENCE_SUFFIXES = (
    "這樣比較看得出對方原本願不願意互動",
    "先讓這次交流保持簡單，不急著處理全部問題",
    "重點是留下清楚選擇，不是逼對方給出答案",
    "做完就先等待，不用立刻安排第二個動作",
    "這一步越簡單，越容易看見沒有被施壓的反應",
    "先把眼前的互動做好，再決定是否談更深的內容",
    "保留彼此停下來的空間，對話才不會變成拉扯",
    "不需要證明你有多努力，只需要確認交流是否順暢",
    "讓對方有拒絕或暫停的空間，才能看見真實意願",
    "先用一次行動驗證，不要連續增加新的要求",
    "把內容減少，才能分辨對方回應的是你，還是只是在應付壓力",
    "先不處理關係名稱，讓這次交流只回到眼前的小事",
    "說完後不要補充理由，讓對方自己決定要不要延續",
    "越能容許對話自然結束，越容易看見對方原本願不願意繼續",
    "這次只改一個地方，才知道什麼做法真的有幫助",
    "不要把安撫、道歉和要求答案全部放在同一段訊息裡",
    "先確認雙方還能平靜交流，再談需要承擔的問題",
    "讓內容容易理解，也讓對方不需要立刻做出關係決定",
    "把目標放在恢復正常交流，不要急著證明彼此仍有感情",
    "先看這個做法能不能讓互動變順，再決定是否繼續花心力",
    "只提出一個清楚需要，不要求對方同時安撫所有情緒",
    "保留一句話就能說完的重點，其餘內容等有回應再談",
    "讓彼此都能選擇暫停，會比一次追完整答案更有幫助",
    "這次交流若能平穩結束，本身就是比長篇解釋更好的開始",
    "不要預先安排對方應該怎麼回，先接受他的真實反應",
    "把行動保持單純，才不會讓試探和修復混在一起",
)

ACTION_STOP_SUFFIXES = (
    "停下來不是認輸，而是避免讓情況繼續惡化",
    "等情緒和生活都回穩，再決定是否需要新的行動",
    "這個界線能保護你，也能避免對方感到被追趕",
    "停止追加訊息，才能看清楚對方會不會自己靠近",
    "先把注意力帶回自己的生活，不必守著回覆等待",
    "如果相同情況持續出現，就把它當成不能忽略的事實",
    "不要為了完成修復，把自己的身心狀態放到最後",
    "對方沒有改變回應方式前，不需要反覆嘗試同一件事",
    "如果停下後仍然很焦急，先找朋友或專業支持整理情緒",
    "這次沒有得到答案，也不需要立刻用新的行動補上空白",
    "把停止條件先想清楚，能避免自己在等待裡越陷越深",
    "界線出現時就尊重，比勉強維持表面聯絡更有幫助",
    "讓一段時間的現實變化說明情況，不用每天重新解讀",
    "如果每次交流後都更不安，就需要重新評估是否值得繼續",
    "你可以在意這段關係，同時拒絕讓自己一直留在消耗裡",
    "先停止反覆嘗試，才能分辨關係是否有對方主動的部分",
)

ACTION_AVOID_SUFFIXES = (
    "避免這些做法，才能看見沒有被逼出來的回應",
    "其中任何一項出現，都容易讓這次交流失去原本的目的",
    "先拿掉這些壓力，才知道對方原本願意互動到哪裡",
    "這些動作只會增加焦急，很難帶來更可靠的答案",
    "如果很想做其中一項，先等情緒平靜後再重新評估",
    "先把它們排除，這次行動才不會又回到舊的拉扯",
    "不做這些事，也是尊重自己和對方界線的一部分",
    "越能避開這些做法，越容易讓真實意願自然出現",
    "這些方式可能換來短暫回應，卻不容易帶來穩定互動",
    "先把它們停下來，才能分清楚關心和施壓的差別",
    "修復不需要靠這些方法證明誠意，清楚和克制更重要",
    "如果必須靠這些做法維持聯絡，就不算雙方自然參與",
    "避開這些行動，能減少對方只因壓力而回覆的可能",
    "先不做這些事，才有空間觀察對方會不會自己靠近",
    "這些做法容易讓小問題升高，不適合拿來測試感情",
    "讓這次互動保持簡單，比增加更多方法更能看清現況",
)

ACTION_REPAIR_HEADLINES = {
    "unknown": "先處理能確認的問題",
    "communication-repair": "先把重點說清楚",
    "outer-intensity": "先看實際行動",
    "identity-rhythm": "先離開對錯評價",
    "emotional-safety": "先讓彼此說話時更安心",
    "saturn-pressure": "先拆小責任問題",
    "action-conflict": "先讓口氣降下來",
    "attraction-pursuit": "先別把熱度當答案",
}

ACTION_MODE_HEADLINE_TAGS = {
    "boundary-only": "界線未改變就不靠近",
    "observe-or-single-low-stimulation-test": "只保留一次簡短互動",
    "shared-space-boundary": "共同場合不談判感情",
    "small-bid-response-led": "由他的回應決定是否繼續",
    "tone-repair-in-existing-channel": "先用原本聯絡方式修正口氣",
}


def sentence(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip(" ，。；;\n")
    return f"{text}。" if text else ""


def join_sentences(*values: str) -> str:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        current = sentence(value)
        normalized = re.sub(r"\s+", "", current)
        if not current or normalized in seen:
            continue
        seen.add(normalized)
        output.append(current)
    return "".join(output)


def sign_name(value_key: str) -> str:
    return value_key.split(".", 1)[1] if "." in value_key else "unknown"


def signal_base(kind: str, pair_key: str) -> str:
    if kind == "attraction":
        return ATTRACTION_PAIRS.get(pair_key, "")
    if kind == "friction":
        return FRICTION_PAIRS.get(pair_key, "")
    return GROWTH_PAIRS.get(pair_key, "")


def person_possessive(person_key: str) -> str:
    return "你的" if person_key == "persona" else "他的"


SIGNAL_ASPECT_TONES = {
    "attraction": {
        "conjunction": "集中",
        "sextile": "輕鬆",
        "trine": "自然",
        "square": "易卡",
        "opposition": "拉扯",
        "quincunx": "錯拍",
    },
    "friction": {
        "conjunction": "疊高",
        "sextile": "可調",
        "trine": "可解",
        "square": "碰撞",
        "opposition": "拉扯",
        "quincunx": "錯拍",
    },
    "growth": {
        "conjunction": "需要集中處理",
        "sextile": "較容易開始",
        "trine": "較容易延續",
        "square": "需要刻意調整",
        "opposition": "需要兩邊配合",
        "quincunx": "需要重新對齊",
    },
}


def directional_signal_forms(signal: RelationshipSignal) -> RealizationForms:
    actor = f"{person_possessive(signal.actor_person)}{PLANET_FUNCTIONS[signal.actor_planet]}"
    receiver = f"{person_possessive(signal.receiver_person)}{PLANET_FUNCTIONS[signal.receiver_planet]}"
    base = signal_base(signal.kind, signal.pair_key)
    if not base:
        raise ValueError(f"unsupported relationship signal realization: {signal.raw}")
    kind_focus = {
        "attraction": "吸引",
        "friction": "摩擦",
        "growth": "調整空間",
    }[signal.kind]
    tone = SIGNAL_ASPECT_TONES[signal.kind][signal.aspect]
    return RealizationForms(
        direct=f"{tone}的{kind_focus}來自{actor}牽動{receiver}，{base}",
        situational=f"{tone}時，{actor}一明顯，{receiver}也會被帶動，{base}",
        relational=f"{kind_focus}{tone}時，{actor}會牽動{receiver}，{base}",
    )


def signal_sentence(
    kind: str,
    value_key: str,
    purpose: RealizationPurpose = "direct",
) -> str:
    if "unresolved" in value_key or value_key in {"unknown", "none"}:
        return ""
    signal = parse_relationship_signal(value_key, expected_kind=kind)
    forms = directional_signal_forms(signal)
    forms.validate(f"{kind}:{value_key}")
    return forms.for_purpose(purpose)


def render_final_narrative_section(
    *,
    section_id: str,
    facts: ValidatedFinalNarrativeFactContract,
    seed: str,
) -> RenderedReaderSection:
    # Imported lazily so page modules can reuse the shared, controlled language
    # banks above without creating an import cycle during module initialization.
    from .final_narrative_pages import PAGE_RENDERERS

    renderer = PAGE_RENDERERS.get(section_id)
    if renderer is None:
        raise ValueError(f"Unsupported final narrative section: {section_id}")
    reader = SectionFactReader(contract=facts, section_id=section_id)
    rendered = renderer(reader, seed)
    reader.assert_complete()
    validate_page_grammar(section_id, rendered)
    return RenderedReaderSection(**rendered)
