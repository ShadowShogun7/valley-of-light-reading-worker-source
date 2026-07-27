"""Reader-language realization for the timing-reading page."""

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
    join_sentences,
)
from ..final_narrative_realization import RealizationForms, domain_index, realize, select_context_variant
from ..final_narrative_semantic_coverage import (
    FinalNarrativeSemanticCoverageError,
    SectionFactReader,
    require_supported_value,
)
from ..final_narrative_semantic_domains import CONTACT_STATUS_KEYS, QUESTION_KEYS


TIMING_NATIVE_ZH_TW_CATALOG_VERSION = "timing-native-zh-tw-catalog-v5"


class TimingNativeChineseError(ValueError):
    """Raised when timing copy is unsupported, untraceable, or unnatural."""


QUESTIONS = {
    "still-love-me",
    "any-chance",
    "when-to-contact",
    "what-did-i-do-wrong",
    "stay-or-let-go",
}
CONTACT_STATUSES = {
    "blocked",
    "no-contact",
    "occasional-contact",
    "still-in-contact",
    "living-or-working-together",
}

ACTION_HEADLINES = {
    "avoid-push": ("現在先不要急著往前", "先避開容易增加壓力的靠近", "這段時間適合放慢，不適合逼答案"),
    "low-pressure-message": ("可以開口，但訊息要短", "適合一次輕鬆而沒有要求的聯絡", "現在只適合簡短試探互動"),
    "observe-for-soft-window": ("先等氣氛放鬆，再決定要不要開口", "目前以觀察為主，不急著選日期", "等互動自然變柔和再靠近"),
    "observe-only": ("現在先觀察他的實際反應", "暫時不要主動加快關係", "這段時間先讓答案從行動出現"),
    "not-calculated": ("目前沒有足夠資料指定時段", "時機資料不足，先看現有聯絡狀態", "先用現實互動決定是否聯絡"),
}

ACTION_COPY = {
    "avoid-push": "把重要話題延後，先不要要求關係定位或立即答覆",
    "low-pressure-message": "只傳一件容易回答的小事，送出後不要立刻補第二段",
    "observe-for-soft-window": "等對話不再明顯緊繃，再考慮一次簡短聯絡",
    "observe-only": "先觀察對方是否主動靠近，不用安排新的測試",
    "not-calculated": "不要為了找完美日期忽略對方現在的真實界線",
}

TIMING_ACTION_VARIANTS = {
    "avoid-push": (
        ACTION_COPY["avoid-push"],
        "這次先不談關係定位，把需要立即答覆的問題留到後面",
        "先停止追問未來和承諾，不在這段時間把話題加重",
        "重要問題先不往前推，等對話比較放鬆再重新判斷",
        "現在只維持原本的聯絡程度，不另外安排關係對話",
        "這次不要要求對方說明未來，先讓容易卡住的話題停下",
        "先避開承諾、定位和結果，只保留必要而簡單的互動",
        "不用趕在這段時間取得答案，先把靠近的速度停在原位",
        "如果話題會帶到未來或責任，這次就先不開啟",
        "現在先不測試對方的態度，也不用一次訊息逼近關係結論",
        "保留現有界線，不在這個時段加入需要對方表態的內容",
        "先不提復合、承諾或關係方向，等互動不再那麼緊再談",
        "這次不主動延長話題，讓雙方先回到沒有結果壓力的互動",
        "先把想問的重要答案留下，現在不要要求對方當場說清楚",
        "這段時間只適合少做一步，不適合用新聯絡推動關係",
    ),
    "low-pressure-message": (
        ACTION_COPY["low-pressure-message"],
        "只用一句話開一個日常話題，說完就先停",
        "傳一則不需要對方立即表態的簡短訊息",
        "這次只問一件容易回答的小事，不另外補充",
        "用原本的聯絡方式簡短開口，讓話題能自然結束",
    ),
    "observe-for-soft-window": (
        ACTION_COPY["observe-for-soft-window"],
        "等對話的口氣不再那麼緊，再安排一次簡短聯絡",
        "先觀察互動是否自然回暖，不用現在就確定日期",
        "等原本的緊繃感下降後，只保留一次輕鬆開口",
        "先看幾天內有沒有比較柔和的反應，再決定要不要聯絡",
    ),
    "observe-only": (
        ACTION_COPY["observe-only"],
        "現在不安排新訊息，先看對方會不會自己靠近",
        "先保留原本狀態，不用再做一次聯絡測試",
        "把這段時間用來看實際變化，不主動增加互動",
        "先等對方的行動出現，沒有新回應就不往前加",
    ),
    "not-calculated": (
        ACTION_COPY["not-calculated"],
        "沒有可靠時機資料時，就依現在的聯絡界線行動",
        "先用對方實際接受的互動程度決定是否開口",
        "不為了找日期另外製造聯絡，先尊重眼前狀態",
        "時機不明確時，就不超過對方目前已經開放的範圍",
    ),
}

TIMING_ACTION_FORMS = {
    key: RealizationForms(ACTION_COPY[key], ACTION_HEADLINES[key][0], ACTION_HEADLINES[key][1])
    for key in ACTION_COPY
}

CONTACT_STATUS_COPY = {
    "blocked": (
        "聯絡方式仍被關上時，不要換方法接近，先等對方自己改變界線",
        "目前的聯絡界線很清楚，不適合用新帳號、朋友或共同場合繞過它",
        "對方還沒有重開聯絡方式以前，任何時段都先以不接觸為上限",
        "現在不是挑日子的問題，而是原本的聯絡界線還沒有鬆動",
        "界線未改變時，最重要的時機訊息就是先不主動靠近",
    ),
    "no-contact": (
        "目前沒有自然聯絡，先看是否會出現不靠你連續推動的互動",
        "現在沒有持續對話，聯絡以前要先承認關係仍停在沉默裡",
        "雙方目前沒有自然互動，不適合只靠一個較順時段就往前推",
        "沒有聯絡的狀態還沒有改變，時機判斷要先尊重這個事實",
        "現在最需要看的是沉默會不會自然鬆動，不是先增加聯絡次數",
    ),
    "occasional-contact": (
        "只有零星回應時，先看他會不會主動開啟下一次對話",
        "目前的聯絡不穩定，適合時機要看他是否也會自己開口",
        "偶爾說上話只能說明還有對話空間，還不足以把話題加重",
        "零星回應之間還有很多空白，聯絡節奏不適合突然加快",
        "目前可以保留簡單互動，但時機要由下一次是否自然出現來確認",
    ),
    "still-in-contact": (
        "既然還能聊天，重點是他是否也會主動開新話題",
        "目前還有對話，因此時機的關鍵是話題能不能保持自然",
        "你們仍有聯絡，不需要另外製造機會，先看他是否也會維持對話",
        "現在不缺開口的管道，缺的是這份互動有沒有雙方一起往下帶",
        "日常仍能說話時，適合程度要看對話有沒有越來越緊",
    ),
    "living-or-working-together": (
        "共同場合仍有接觸時，先維持自然，不要利用見面機會逼談關係",
        "你們還會因日常或工作見面，這不等於共同場合適合談感情",
        "目前的接觸有實際原因，時機判斷不能把必要往來當成主動靠近",
        "共同生活或工作空間要先保持安全，不適合用現場機會逼出答案",
        "還會碰面並不表示關係已放鬆，先看日常相處能不能回到自然",
    ),
}

CONTACT_POSTURE_HEADLINES = {
    "boundary-first": "界線沒有改變前先停",
    "observe-channel": "先看聯絡會不會自然恢復",
    "protect-shared-space": "先保護共同場合的日常",
    "test-low-pressure": "只保留一次輕鬆開口",
    "watch-initiation": "先看對話能不能維持自然",
}

TIMING_HEADLINE_COPY = {
    "still-love-me": {
        "avoid-push": "現在先放慢，讓他的行動回答心意",
        "low-pressure-message": "可以簡短開口，再看他會不會主動延續",
        "observe-for-soft-window": "先等對話放鬆，再看他會不會主動靠近",
        "observe-only": "現在先不增加聯絡，觀察他會不會主動",
        "not-calculated": "先看他目前怎麼回應，不用急著挑日期",
    },
    "any-chance": {
        "avoid-push": "現在先放慢，看看舊問題有沒有改變",
        "low-pressure-message": "可以簡短開口，先看互動是否真的不同",
        "observe-for-soft-window": "先等氣氛放鬆，再看舊問題有沒有改變",
        "observe-only": "暫時不要推進，先看雙方做法有沒有改變",
        "not-calculated": "先看現實互動有沒有改變，不用急著挑日期",
    },
    "when-to-contact": {
        "avoid-push": "現在先不要開口，避免讓壓力繼續增加",
        "low-pressure-message": "可以簡短開口，但不要要求立即回答",
        "observe-for-soft-window": "先等對話不再緊繃，再考慮聯絡",
        "observe-only": "現在先觀察，不急著安排新的聯絡",
        "not-calculated": "先依目前的聯絡界線決定是否開口",
    },
    "what-did-i-do-wrong": {
        "avoid-push": "現在先放慢，避免再次碰到相同摩擦",
        "low-pressure-message": "可以簡短開口，只處理一件具體問題",
        "observe-for-soft-window": "先等對話放鬆，再修正最重要的誤會",
        "observe-only": "暫時不要補救，先看相同問題會不會再出現",
        "not-calculated": "先看問題怎麼發生，不用急著挑聯絡日期",
    },
    "stay-or-let-go": {
        "avoid-push": "這段時間先放慢，不要在焦急時逼自己決定",
        "low-pressure-message": "可以簡短開口，再看等待有沒有得到回應",
        "observe-for-soft-window": "先等互動放鬆，再看等待是否還有意義",
        "observe-only": "暫時不要增加互動，讓他的行動回答",
        "not-calculated": "先看他現在的選擇，再決定要等還是放下",
    },
}

TIMING_BAND_COPY = {
    "better": (
        "先維持簡單互動，不要因為氣氛放鬆就直接追問關係",
        "可以好好說話，但不要把短暫順利當成關係已經改變",
        "讓對方自己決定願意靠近多少，不要急著把話題加重",
        "可以談眼前的事，但先不要一次問到關係結論",
        "是否繼續往前，仍要看兩個人之後怎麼回應",
    ),
    "neutral": (
        "不用特別搶快，照目前的聯絡界線行動就好",
        "這段時間沒有明顯變化，先維持原本的聯絡方式",
        "是否靠近仍要看雙方的真實回應，不必勉強安排進度",
        "目前的聯絡狀態比日期更重要，先不要改變互動速度",
        "不用趕著行動，也不要為了等一個日期停住自己的生活",
    ),
    "avoid": (
        "重要話題先不要往前推，避免摩擦繼續升高",
        "先不要問關係定位或承諾，小問題很容易在這時被談重",
        "靠近太快容易讓他退開，重要對話先延後",
        "現在比較容易誤會彼此，先不要要求他立刻說明關係方向",
        "責任和界線目前較敏感，一次談太多容易讓對話停住",
        "先不要追著問明確答案，他可能會把確認關係聽成壓力",
        "重話題容易讓回應變得保守，先維持原本的互動速度",
        "現在不適合一次談完整段關係，越急著說清楚越可能只得到沉默",
        "先不要把話題推到未來，討論結果很容易讓互動變僵",
        "不要用聯絡測試關係方向，對方目前較難立即表態",
        "話題一變重，對話就容易失去原本的自然",
        "先把承諾和關係定位延後，避免對方立刻防備",
        "這時更容易出現防備和誤會，不要用追問換取回應",
        "如果沒有必要聯絡，先不要增加新的感情話題",
        "重要對話容易偏離重點，等彼此比較平靜時再談結果",
    ),
}

TIMING_BAND_FORMS = {
    key: RealizationForms(*values[:3])
    for key, values in TIMING_BAND_COPY.items()
}

TIMING_PARAGRAPH_BAND_COPY = {
    "better": "那段時間你們可以自然聊眼前的事，但不要因為氣氛放鬆就直接追問關係",
    "neutral": "那段時間你們沒有明顯推力，是否開口仍要看當時的聯絡界線",
    "avoid": "那段時間你們的互動壓力較高，重要話題先不要往前推",
}

TIMING_PARAGRAPH_CAUTIOUS_SOFT_WINDOW = (
    "即使那段時間你們比較好開口，整體壓力仍在，重要話題先不要往前推"
)

PRECISE_DATE_COPY = {
    "available": (
        "即使資料較完整，也只能看一段時間的氣氛，不能保證某一天會成功",
        "日期只能協助調整做法，不能預先決定對方會不會回應",
        "可以參考較順的時段，但不能把其中一天當成唯一機會",
        "資料完整只能讓區間更清楚，不能保證對方會在某天回應",
        "這些日期用來避開高壓時段，不是預測關係結果",
        "可以用時段調整開口方式，但對方願不願意互動仍由他決定",
        "日期訊息較精細，仍不能把一天寫成必然成功的機會",
        "即使能看到較好的區間，現有界線也不會因為日期自動消失",
        "時機可以提醒你什麼時候要保守，不能替雙方做出關係選擇",
        "這些日子只能影響談話氣氛，不能證明對方已經準備好",
        "資料足夠細也不等於能預告回覆，當下反應仍是最後依據",
        "可以選擇壓力較輕的區間，但不能越過對方已經表明的界線",
        "精細時機只是決定做法的參考，不是對感情的預告",
        "這個時段可以幫你決定快慢，不能決定對方會怎麼選擇",
        "日期能提供的是氣氛參考，關係會不會改變仍要看實際行動",
    ),
    "unavailable": (
        "目前只適合看一段時間的氣氛，不適合指定某一天一定有效",
        "目前無法把時機縮到特定日期，只能保留較適合觀察的區間",
        "現在只能判斷一段時間的氣氛，不能預告哪一天會得到回應",
        "這份資料適合用來調整快慢，不適合挑出保證有效的日子",
        "時機只能看大致區間，真正變化仍要由當時互動確認",
        "目前的出生或時機資料不適合縮到某一天，只能保留較寬的範圍",
        "現在無法負責任地指定日期，判斷要回到對方當下的聯絡界線",
        "資料只能說明一段時間的氣氛，不能選出保證有效的日子",
        "時機精度不足時，不應把寬鬆區間寫成精準預測",
        "現有資料不能支持特定日期，因此只調整互動快慢，不預告回應",
        "目前可以看方向，不能看單日結果，對方的意願仍以實際行動為準",
        "資料不足以挑出一天，只適合說哪一段時間較需要保守",
        "日期不能再縮小時，就不用猜測補出一個看似精準的答案",
        "現在能提供的是時段趨勢，不能預告哪一天會出現新進展",
        "缺少精確資料時，現有聯絡狀態比任何日期都更可靠",
        "現在只能提供大致時段，不能把其中一天寫成必然轉折",
        "缺少精確時間資料時，先用區間調整做法，不推測哪天一定有回應",
        "目前能確認的是整體快慢，不是某一天的結果",
    ),
}

WINDOW_CATEGORY_COPY = {
    "softening": "softening",
    "conflict-risk": "conflict-risk",
    "communication-opening": "communication-opening",
    "boundary-pressure": "boundary-pressure",
    "general-climate": "general-climate",
}

TRIGGER_CONTEXT = {
    "mercury": "你們說話時會更直接",
    "venus": "你們示好時會更直接",
    "mars": "你們靠近時反應會更快",
    "saturn": "你們談責任時態度會更清楚",
    "jupiter": "你們談未來時期待會更清楚",
    "moon": "你們的情緒需要更容易被看見",
    "sun": "你們在意是否被重視的反應更直接",
}

ASPECT_KEYS = {"conjunction", "sextile", "square", "trine", "opposition", "quincunx"}
ASPECT_DOMAIN = ("conjunction", "sextile", "square", "trine", "opposition", "quincunx")
WINDOW_TRIGGER_KEYS = tuple(
    f"{left}-{right}"
    for left in TRIGGER_CONTEXT
    for right in TRIGGER_CONTEXT
)
TIMING_THEME_PHRASES = {
    "mercury": "彼此怎麼說話",
    "venus": "怎麼表達好感",
    "mars": "靠近的速度",
    "saturn": "彼此能承擔多少",
    "jupiter": "未來怎麼安排",
    "moon": "彼此的感受",
    "sun": "有沒有被重視",
}

TIMING_WINDOW_EFFECT_COPY = {
    "softening": {
        "conjunction": "對話比較放鬆，兩個人的反應也更直接",
        "sextile": "對話比較放鬆，也比較接得住對方的回應",
        "trine": "對話比較自然，不需要刻意找話題",
        "square": "比較好開口，但仍可能互相頂住",
        "opposition": "比較好開口，但靠近時仍可能一進一退",
        "quincunx": "比較好開口，但彼此步調仍可能對不上",
    },
    "conflict-risk": {
        "conjunction": "小摩擦會被放大，兩個人的反應也會更直接",
        "sextile": "仍可能有摩擦，但停一下通常還能調整",
        "trine": "仍可能有摩擦，但比較容易說回原本的問題",
        "square": "小摩擦很容易被放大，彼此也容易互相頂住",
        "opposition": "小摩擦會被放大，靠近時也可能一進一退",
        "quincunx": "小摩擦會被放大，彼此步調也可能對不上",
    },
    "communication-opening": {
        "conjunction": "比較能說到重點，但反應也更直接",
        "sextile": "比較能說到重點，也更聽得懂彼此",
        "trine": "比較能把話說清楚，對話也更自然",
        "square": "比較好開口，但仍可能很快互相頂住",
        "opposition": "比較好開口，但仍可能各說各話",
        "quincunx": "比較好開口，但說話步調仍可能對不上",
    },
    "boundary-pressure": {
        "conjunction": "兩個人的態度會更直接",
        "sextile": "彼此仍然能商量",
        "trine": "通常能平穩地把話說完",
        "square": "雙方很快就會防備",
        "opposition": "彼此可能先拉開距離",
        "quincunx": "彼此的步調可能對不上",
    },
    "general-climate": {
        "conjunction": "互動速度會變快，兩個人的態度也會更直接",
        "sextile": "互動會有變化，但彼此比較願意配合",
        "trine": "互動會有變化，整體相處也比較自然",
        "square": "互動速度會變快，一著急就可能互相頂住",
        "opposition": "互動會有變化，靠近時仍可能一進一退",
        "quincunx": "互動會有變化，兩個人的步調可能對不上",
    },
}

CAUTIOUS_SOFT_WINDOW_COPY = (
    "整體壓力仍在，先不要推進重要話題",
    "先不要談關係結果，讓這次對話保持簡單",
    "仍只適合簡單互動，不要要求明確答案",
    "責任和界線仍然敏感，重要問題先保留",
    "可以看看彼此是否放鬆，但不要因此加快關係",
    "先觀察對方怎麼回應，不要把話題往前推",
    "仍要避開承諾、定位和結果問題",
    "目前還不適合談完整段關係，只處理眼前的事",
    "只保留簡短互動，不要用這段時間確認關係",
    "原本的問題還沒有消失，先不要增加重要話題",
    "短暫放鬆不代表界線改變，只看能不能自然說話",
    "仍要讓對話隨時可以停下，不要一次談太多",
)

TIMING_BAND_FOLLOWUPS = (
    "先讓現有互動決定速度",
    "不要用日期跳過目前界線",
    "下一步仍要看對方真實回應",
    "這時保留停下來的空間比較重要",
    "一次只處理眼前能承受的內容",
    "不用趕著在這段時間取得答案",
    "關係是否往前仍由雙方行動決定",
    "氣氛只能調整做法，不能代替意願",
    "先看對話能不能保持自然",
    "沒有回應時就不要增加新的動作",
    "先避免把短期感受放大成結論",
    "等現實狀態改變再重新判斷",
)

TIMING_PRECISION_FOLLOWUPS = (
    "仍要以當時回應為準",
    "這樣比較不會把日期當成保證",
    "真正答案仍在雙方選擇裡",
    "不要因此忽略已經說明的界線",
    "只能用來決定要快一點還是慢一點",
    "沒有自然互動時就先不要靠近",
    "對方的意願不會由日期替他決定",
    "仍要保留事情沒有改變的可能",
    "先把它當作參考而不是結果",
    "後續行動比日子本身更重要",
    "不要為了等時機一直停在原地",
    "當下氣氛和長期選擇需要分開看",
)

TIMING_CAUTION_FOLLOWUPS = (
    "最後仍看實際回應",
    "不能拿來替對方做決定",
    "現有界線仍然優先",
    "沒有新行動就先保留",
    "不要因此增加聯絡次數",
    "較順也不代表一定成功",
    "仍要允許對方暫時不回",
    "這只能協助調整做法",
    "不能把氣氛當成承諾",
    "長期變化比短期感受重要",
    "先確認自己沒有越過界線",
    "真正修復仍需要雙方參與",
)

UNRESOLVED_WINDOW_COPY = (
    "目前沒有足夠資料指出某個時段特別適合靠近",
    "目前看不出哪一段時間明顯比其他時候更適合開口",
    "這次沒有足夠的時間線索可以指定較順的區間",
    "目前只能依照真實互動調整，不能另外挑出一段有利時機",
    "現有資料不足以指出特別適合或需要避開的時段",
)


def format_period(value: str) -> str:
    match = re.fullmatch(r"(\d{4})-(\d{2})-(early|mid|late)", value)
    if not match:
        raise FinalNarrativeSemanticCoverageError(
            f"timing-reading:timing-window has invalid period: {value}"
        )
    third = {"early": "上旬", "mid": "中旬", "late": "下旬"}[match.group(3)]
    return f"{match.group(1)} 年 {int(match.group(2))} 月{third}"


def timing_trigger_context(value: str) -> str:
    parts = value.split("-", 1)
    if len(parts) != 2:
        raise FinalNarrativeSemanticCoverageError(
            f"timing-reading:timing-window has invalid trigger: {value}"
        )
    left, right = parts
    for planet in (left, right):
        require_supported_value(
            section_id="timing-reading",
            role="timing-window-trigger",
            value=planet,
            supported=set(TIMING_THEME_PHRASES),
        )
    left_phrase = TIMING_THEME_PHRASES[left]
    if left == right:
        return f"你們談到{left_phrase}時"
    right_phrase = TIMING_THEME_PHRASES[right]
    return f"你們談到{left_phrase}或{right_phrase}時"


def timing_window_sentence(value_key: str, index: int) -> str:
    parts = value_key.split("|")
    if len(parts) != 4:
        raise FinalNarrativeSemanticCoverageError(
            f"timing-reading:timing-window has invalid value: {value_key}"
        )
    period_key, category, trigger, aspect = parts
    if period_key == "not-calculated" or "unknown" in {period_key, category, trigger, aspect}:
        return select_context_variant(
            UNRESOLVED_WINDOW_COPY,
            index,
            identity="timing-reading:unresolved-window",
        )
    require_supported_value(
        section_id="timing-reading",
        role="timing-window-category",
        value=category,
        supported=set(WINDOW_CATEGORY_COPY),
    )
    require_supported_value(
        section_id="timing-reading",
        role="timing-window-aspect",
        value=aspect,
        supported=ASPECT_KEYS,
    )
    del index
    period = format_period(period_key)
    return (
        f"{period}，{timing_trigger_context(trigger)}，"
        f"{TIMING_WINDOW_EFFECT_COPY[category][aspect]}"
    )


def timing_band_sentence(band: str, window_value: str, index: int) -> str:
    del index
    parts = window_value.split("|")
    category = parts[1] if len(parts) == 4 else "unknown"
    if band == "avoid" and category == "softening":
        return TIMING_PARAGRAPH_CAUTIOUS_SOFT_WINDOW
    return TIMING_PARAGRAPH_BAND_COPY[band]


def single_fact(facts: SectionFactReader, role: str) -> dict[str, Any]:
    records = facts.records(role)
    if len(records) != 1:
        raise FinalNarrativeSemanticCoverageError(
            f"{facts.section_id}: expected one {role} fact, got {len(records)}"
        )
    return records[0]


def render_timing_reading(facts: SectionFactReader, seed: str) -> dict[str, str]:
    del seed
    question_fact = single_fact(facts, "question")
    contact_fact = single_fact(facts, "contact-status")
    posture_fact = single_fact(facts, "timing-posture")
    action_fact = single_fact(facts, "recommended-action")
    band_fact = single_fact(facts, "timing-band")
    contact_posture_fact = single_fact(facts, "contact-posture")
    precise_fact = single_fact(facts, "precise-dates-available")
    window_facts = facts.records("timing-window")

    question = str(question_fact.get("valueKey") or "")
    contact = str(contact_fact.get("valueKey") or "")
    posture = str(posture_fact.get("valueKey") or "")
    action = str(action_fact.get("valueKey") or "")
    band = str(band_fact.get("valueKey") or "")
    contact_posture = str(contact_posture_fact.get("valueKey") or "")
    precise = str(precise_fact.get("valueKey") or "")
    window_values = [str(item.get("valueKey") or "") for item in window_facts]

    require_supported_value(section_id=facts.section_id, role="question", value=question, supported=QUESTION_KEYS)
    require_supported_value(section_id=facts.section_id, role="contact-status", value=contact, supported=CONTACT_STATUS_KEYS)
    require_supported_value(section_id=facts.section_id, role="timing-posture", value=posture, supported=set(ACTION_HEADLINES))
    require_supported_value(section_id=facts.section_id, role="recommended-action", value=action, supported=set(ACTION_HEADLINES))
    require_supported_value(section_id=facts.section_id, role="timing-band", value=band, supported=set(TIMING_BAND_COPY))
    require_supported_value(section_id=facts.section_id, role="contact-posture", value=contact_posture, supported=set(CONTACT_POSTURE_HEADLINES))
    require_supported_value(section_id=facts.section_id, role="precise-dates-available", value=precise, supported=set(PRECISE_DATE_COPY))
    if posture != action:
        raise FinalNarrativeSemanticCoverageError(
            f"timing-reading: timing posture {posture} disagrees with recommended action {action}"
        )
    if contact == "blocked" and action != "avoid-push":
        raise FinalNarrativeSemanticCoverageError(
            "timing-reading: blocked contact must use avoid-push"
        )
    if len(window_values) > 1:
        raise FinalNarrativeSemanticCoverageError("timing-reading: more than one selected timing window")

    window_value = window_values[0] if window_values else "missing|unknown|unknown|unknown"
    contact_index = (
        domain_index(
            contact,
            CONTACT_STATUS_KEYS,
            identity="timing-reading:contact-status",
        )
        * 5
        + domain_index(
            contact_posture,
            tuple(CONTACT_POSTURE_HEADLINES),
            identity="timing-reading:contact-posture",
        )
    )
    action_index = domain_index(
        action,
        tuple(TIMING_ACTION_VARIANTS),
        identity="timing-reading:recommended-action",
    )
    precision_index = domain_index(
        precise,
        tuple(PRECISE_DATE_COPY),
        identity="timing-reading:precise-dates-available",
    )
    window_parts = window_value.split("|")
    window_category = window_parts[1] if len(window_parts) == 4 else "unknown"
    band_index = domain_index(
        band,
        tuple(TIMING_BAND_COPY),
        identity="timing-reading:timing-band",
    ) * 7
    if window_category in WINDOW_CATEGORY_COPY:
        band_index += domain_index(
            window_category,
            tuple(WINDOW_CATEGORY_COPY),
            identity="timing-reading:timing-window-category",
        )

    contact_copy = select_context_variant(
        CONTACT_STATUS_COPY[contact],
        contact_index,
        identity="timing-reading:contact-status",
    )
    action_copy = select_context_variant(
        TIMING_ACTION_VARIANTS[action],
        action_index,
        identity="timing-reading:recommended-action",
    )
    if window_values:
        if window_value.startswith("not-calculated") or "unknown" in window_value:
            facts.record_unknown_fallback("timing-window", window_value, "timing-window-unresolved")
        window_sentence = timing_window_sentence(window_value, 0)
    else:
        facts.record_unknown_fallback("timing-window", "missing", "timing-window-unresolved")
        window_sentence = select_context_variant(
            UNRESOLVED_WINDOW_COPY,
            0,
            identity="timing-reading:missing-window",
        )
    band_sentence = timing_band_sentence(
        band,
        window_value,
        band_index,
    )
    precision_sentence = select_context_variant(
        PRECISE_DATE_COPY[precise],
        precision_index,
        identity="timing-reading:precision",
    )
    headline = TIMING_HEADLINE_COPY[question][action]
    rendered = {
        "headline": headline,
        "meaning": join_sentences(contact_copy),
        "body": join_sentences(
            window_sentence,
            band_sentence,
        ),
        "nextMove": join_sentences(action_copy),
        "caution": join_sentences(precision_sentence),
    }
    frames: dict[str, ReaderMeaningFrame] = {
        "posture": frame_from_fact(
            posture_fact,
            scene_key=f"timing-headline.{question}",
            purpose="direct",
            certainty="conditional",
        ),
        "contact": frame_from_fact(
            contact_fact,
            scene_key=f"contact-permission.{contact_posture}",
            purpose="direct",
            certainty="observed",
        ),
        "band": frame_from_fact(
            band_fact,
            scene_key="overall-timing-band",
            purpose="situational",
            certainty="bounded",
        ),
        "action": frame_from_fact(
            action_fact,
            scene_key="timing-action",
            purpose="direct",
            certainty="conditional",
        ),
        "precision": frame_from_fact(
            precise_fact,
            scene_key="timing-precision-boundary",
            purpose="direct",
            certainty="bounded" if precise == "available" else "unknown",
        ),
    }
    if window_facts:
        frames["window"] = frame_from_fact(
            window_facts[0],
            scene_key="selected-timing-window",
            purpose="situational",
            certainty=(
                "unknown"
                if window_value.startswith("not-calculated") or "unknown" in window_value
                else "bounded"
            ),
        )
    plan_steps = [
        ("headline", frames["posture"]),
        ("opening", frames["contact"]),
    ]
    if "window" in frames:
        plan_steps.append(("elaboration", frames["window"]))
    plan_steps.extend(
        (
            ("condition", frames["band"]),
            ("action", frames["action"]),
            ("boundary", frames["precision"]),
        )
    )
    plan = paragraph_plan(
        section_id=facts.section_id,
        paragraph_kind="contact-window-decision",
        conclusion_key=f"{question}-{contact}-{action}-{band}",
        steps=plan_steps,
        supports=(
            support_from_fact(question_fact),
            support_from_fact(contact_posture_fact),
        ),
    )
    validate_timing_rendered(rendered, frames=frames)
    validate_paragraph_output(plan, rendered)
    return rendered


def split_sentences(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[。！？!?]+", value) if item.strip()]


@lru_cache(maxsize=1)
def timing_static_sentence_traces() -> dict[str, dict[str, str]]:
    traces: dict[str, dict[str, str]] = {}

    def add(text: str, trace: dict[str, str]) -> None:
        normalized = normalize_copy(text)
        existing = traces.get(normalized)
        if existing is not None and existing != trace:
            raise TimingNativeChineseError(
                f"timing sentence has ambiguous trace: {text}"
            )
        traces[normalized] = trace

    for question, action_copy in TIMING_HEADLINE_COPY.items():
        for action, headline in action_copy.items():
            add(
                headline,
                {
                    "kind": "composition",
                    "role": "timing-posture",
                    "valueKey": action,
                    "purpose": "headline",
                    "sceneKey": f"timing-headline.{question}",
                },
            )
    for contact, values in CONTACT_STATUS_COPY.items():
        for text in values:
            add(
                text,
                {
                    "kind": "fact-realization",
                    "role": "contact-status",
                    "valueKey": contact,
                    "purpose": "direct",
                },
            )
    for band, values in TIMING_BAND_COPY.items():
        for text in values:
            add(
                text,
                {
                    "kind": "fact-realization",
                    "role": "timing-band",
                    "valueKey": band,
                    "purpose": "situational",
                },
            )
    for band, text in TIMING_PARAGRAPH_BAND_COPY.items():
        add(
            text,
            {
                "kind": "paragraph-realization",
                "role": "timing-band",
                "valueKey": band,
                "purpose": "situational",
            },
        )
    add(
        TIMING_PARAGRAPH_CAUTIOUS_SOFT_WINDOW,
        {
            "kind": "paragraph-realization",
            "role": "timing-band",
            "valueKey": "avoid",
            "purpose": "situational",
        },
    )
    for text in CAUTIOUS_SOFT_WINDOW_COPY:
        add(
            text,
            {
                "kind": "fact-realization",
                "role": "timing-band",
                "valueKey": "avoid",
                "purpose": "situational",
            },
        )
    for action, values in TIMING_ACTION_VARIANTS.items():
        for text in values:
            add(
                text,
                {
                    "kind": "fact-realization",
                    "role": "recommended-action",
                    "valueKey": action,
                    "purpose": "direct",
                },
            )
    for precision, values in PRECISE_DATE_COPY.items():
        for text in values:
            add(
                text,
                {
                    "kind": "fact-realization",
                    "role": "precise-dates-available",
                    "valueKey": precision,
                    "purpose": "direct",
                },
            )
    for text in UNRESOLVED_WINDOW_COPY:
        add(
            text,
            {
                "kind": "fact-realization",
                "role": "timing-window",
                "purpose": "situational",
                "certainty": "unknown",
            },
        )
    return traces


@lru_cache(maxsize=4096)
def timing_sentence_trace(sentence: str) -> dict[str, str] | None:
    normalized = normalize_copy(sentence)
    static = timing_static_sentence_traces().get(normalized)
    if static is not None:
        return static
    period_match = re.search(
        r"(\d{4}) 年 (\d{1,2}) 月(上旬|中旬|下旬)",
        sentence,
    )
    if period_match is None:
        return None
    third = {"上旬": "early", "中旬": "mid", "下旬": "late"}[
        period_match.group(3)
    ]
    period_key = f"{period_match.group(1)}-{int(period_match.group(2)):02d}-{third}"
    for category in WINDOW_CATEGORY_COPY:
        for trigger in WINDOW_TRIGGER_KEYS:
            for aspect in ASPECT_DOMAIN:
                value_key = f"{period_key}|{category}|{trigger}|{aspect}"
                if normalize_copy(timing_window_sentence(value_key, 0)) == normalized:
                    return {
                        "kind": "fact-realization",
                        "role": "timing-window",
                        "valueKey": value_key,
                        "purpose": "situational",
                    }
    return None


def assert_frame_trace(
    text: str,
    frame: ReaderMeaningFrame,
    *,
    purpose: str,
) -> None:
    sentences = split_sentences(text)
    if len(sentences) != 1:
        raise TimingNativeChineseError(
            f"timing sentence ownership is ambiguous: {text}"
        )
    trace = timing_sentence_trace(sentences[0])
    if trace is None:
        raise TimingNativeChineseError(f"untraceable timing sentence: {sentences[0]}")
    if trace.get("role") != frame.role or trace.get("purpose") != purpose:
        raise TimingNativeChineseError(
            f"timing sentence trace does not match frame: {trace}"
        )
    trace_value = str(trace.get("valueKey") or "")
    if trace_value and trace_value != frame.value_key:
        raise TimingNativeChineseError(
            f"timing sentence trace has stale value: {trace_value}"
        )
    trace_scene = str(trace.get("sceneKey") or "")
    if trace_scene and trace_scene != frame.scene_key:
        raise TimingNativeChineseError(
            f"timing sentence trace has stale scene: {trace_scene}"
        )


def validate_timing_rendered(
    rendered: Mapping[str, str],
    *,
    frames: Mapping[str, ReaderMeaningFrame],
) -> None:
    for frame in frames.values():
        frame.validate()
        if frame.section_id != "timing-reading":
            raise TimingNativeChineseError(
                f"timing renderer received frame for {frame.section_id}"
            )
    for field, text in rendered.items():
        issues = audit_native_zh_tw_text(text)
        if issues:
            details = ", ".join(f"{item.severity}:{item.id}" for item in issues)
            raise TimingNativeChineseError(
                f"timing-reading:{field}: native Chinese gate failed: {details}"
            )

    assert_frame_trace(rendered["headline"], frames["posture"], purpose="headline")
    assert_frame_trace(rendered["meaning"], frames["contact"], purpose="direct")
    body = split_sentences(rendered["body"])
    if len(body) != 2:
        raise TimingNativeChineseError("timing body must contain window and band")
    if "window" in frames:
        assert_frame_trace(body[0], frames["window"], purpose="situational")
    else:
        trace = timing_sentence_trace(body[0])
        if not trace or trace.get("certainty") != "unknown":
            raise TimingNativeChineseError("missing timing window lacks disclosure")
    assert_frame_trace(body[1], frames["band"], purpose="situational")
    assert_frame_trace(rendered["nextMove"], frames["action"], purpose="direct")
    assert_frame_trace(rendered["caution"], frames["precision"], purpose="direct")


def timing_catalog_errors() -> list[str]:
    errors: list[str] = []
    if set(TIMING_HEADLINE_COPY) != QUESTIONS:
        errors.append("timing headline question registry is incomplete")
    for question, headlines in TIMING_HEADLINE_COPY.items():
        if set(headlines) != set(ACTION_HEADLINES):
            errors.append(f"timing headline action registry is incomplete: {question}")
    try:
        timing_static_sentence_traces()
    except TimingNativeChineseError as exc:
        return [str(exc)]
    copy_values = [
        *(text for values in TIMING_HEADLINE_COPY.values() for text in values.values()),
        *(text for values in CONTACT_STATUS_COPY.values() for text in values),
        *(text for values in TIMING_ACTION_VARIANTS.values() for text in values),
        *(text for values in TIMING_BAND_COPY.values() for text in values),
        *TIMING_PARAGRAPH_BAND_COPY.values(),
        TIMING_PARAGRAPH_CAUTIOUS_SOFT_WINDOW,
        *CAUTIOUS_SOFT_WINDOW_COPY,
        *(text for values in PRECISE_DATE_COPY.values() for text in values),
        *UNRESOLVED_WINDOW_COPY,
        *(
            timing_window_sentence(
                f"2026-07-mid|{category}|{trigger}|{aspect}",
                0,
            )
            for category in WINDOW_CATEGORY_COPY
            for trigger in WINDOW_TRIGGER_KEYS
            for aspect in ASPECT_DOMAIN
        ),
    ]
    for text in copy_values:
        issues = audit_native_zh_tw_text(text)
        if issues:
            errors.append(
                f"{text}: " + ", ".join(f"{item.severity}:{item.id}" for item in issues)
            )
    return errors


__all__ = [
    "ACTION_HEADLINES",
    "TIMING_ACTION_VARIANTS",
    "TIMING_PARAGRAPH_BAND_COPY",
    "TIMING_NATIVE_ZH_TW_CATALOG_VERSION",
    "TimingNativeChineseError",
    "render_timing_reading",
    "timing_catalog_errors",
    "timing_sentence_trace",
    "timing_window_sentence",
    "validate_timing_rendered",
]
