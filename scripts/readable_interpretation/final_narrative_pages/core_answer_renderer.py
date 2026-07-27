"""Reader-language realization for the selected core-question page."""

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
    DYNAMIC_FORMS,
    OBSERVABLE_FORMS,
    PARTNER_MOON_NEED_FORMS,
    join_sentences,
    sign_name,
)
from ..final_narrative_realization import (
    RealizationForms,
    domain_index,
    realize,
    select_context_variant,
)
from ..final_narrative_semantic_coverage import (
    FinalNarrativeSemanticCoverageError,
    SectionFactReader,
    require_supported_value,
)
from ..final_narrative_semantic_domains import (
    CONTACT_STATUS_KEYS,
    QUESTION_KEYS,
    RELATIONSHIP_DYNAMIC_KEYS,
    RELATIONSHIP_STAGE_KEYS,
    RelationshipSignal,
    ZODIAC_SIGNS,
    is_unknown_signal,
)
from ..final_narrative_signal_service import (
    OUTER_PLANETS,
    resolve_relationship_signal,
    supported_evidence_signal_values,
)


CORE_ANSWER_NATIVE_ZH_TW_CATALOG_VERSION = "core-answer-native-zh-tw-catalog-v6"


class CoreAnswerNativeChineseError(ValueError):
    """Raised when core-answer copy is unsupported, untraceable, or unnatural."""


ANSWER_TRACK_HEADLINES = {
    "attraction-evidence": "先看吸引有沒有變成持續靠近",
    "breakup-cause": "真正讓關係停下來的是什麼",
    "cold-war-stuck-point": "冷戰一直沒有鬆開的原因",
    "communication-pattern": "問題常出在彼此怎麼說、怎麼聽",
    "conflict-cycle": "反覆爭吵是怎麼被推高的",
    "contact-boundary": "聯絡以前先確認目前界線",
    "contact-gain-or-loss": "現在開口會拉近還是增加壓力",
    "contact-readiness": "目前是否已經適合重新開口",
    "deescalation-next-step": "先停止讓衝突繼續升高",
    "emotional-safety": "彼此能不能在不防備時說話",
    "hot-cold-pattern": "忽冷忽熱背後的相處節奏",
    "partner-continuation-intent": "他有沒有把關係延續下去的行動",
    "partner-current-view": "他現在如何回應這段關係",
    "pressure-risk": "什麼做法最容易讓他退開",
    "proactive-contact-likelihood": "他會不會自己重新開口",
    "realistic-continuation": "這段關係還有多少現實延續空間",
    "reconciliation-potential": "重新靠近需要哪些真實改變",
    "relationship-development": "這段關係能不能變得更明確",
    "relationship-direction": "目前的行動正把關係帶往哪裡",
    "remaining-feeling": "他的在意是否還留在行動裡",
    "reopen-contact": "重新開口需要先具備什麼",
    "repair-condition": "修復以前必須先改變什麼",
    "repairability": "相同問題還有沒有調整空間",
    "restore-interaction": "怎樣才能恢復自然互動",
    "self-protection": "先分清楚反省和過度自責",
    "serious-potential": "好感有沒有走向認真關係的條件",
    "timing-window": "哪種時段比較能承受重新互動",
    "wait-or-release": "等待是否仍有現實理由",
}

QUESTION_TRACK_PRIORITY = {
    "still-love-me": (
        "remaining-feeling",
        "partner-current-view",
        "partner-continuation-intent",
        "proactive-contact-likelihood",
        "attraction-evidence",
    ),
    "any-chance": (
        "reconciliation-potential",
        "repairability",
        "repair-condition",
        "realistic-continuation",
        "relationship-development",
    ),
    "when-to-contact": (
        "contact-readiness",
        "contact-gain-or-loss",
        "contact-boundary",
        "reopen-contact",
        "restore-interaction",
        "timing-window",
    ),
    "what-did-i-do-wrong": (
        "breakup-cause",
        "conflict-cycle",
        "communication-pattern",
        "emotional-safety",
        "self-protection",
        "pressure-risk",
    ),
    "stay-or-let-go": (
        "wait-or-release",
        "realistic-continuation",
        "relationship-direction",
        "partner-continuation-intent",
    ),
}


CORE_QUESTION_FOCUS_TERMS = {
    ("ambiguous", "still-love-me"): ("認真",),
    ("ambiguous", "any-chance"): ("發展", "往前"),
    ("ambiguous", "when-to-contact"): ("清楚", "定義"),
    ("ambiguous", "what-did-i-do-wrong"): ("忽冷忽熱", "一近一退"),
    ("ambiguous", "stay-or-let-go"): ("觀察", "值得"),
    ("broke-up-recent", "still-love-me"): ("心意", "在意", "感情", "心裡"),
    ("broke-up-recent", "any-chance"): ("復合", "修復"),
    ("broke-up-recent", "when-to-contact"): ("恢復互動",),
    ("broke-up-recent", "what-did-i-do-wrong"): ("分手", "原因", "自責"),
    ("broke-up-recent", "stay-or-let-go"): ("穩住", "穩下來", "等待"),
    ("broke-up-long", "still-love-me"): ("看你", "怎麼看", "看待", "態度", "伴侶位置"),
    ("broke-up-long", "any-chance"): ("延續", "現實"),
    ("broke-up-long", "when-to-contact"): ("重新開口",),
    ("broke-up-long", "what-did-i-do-wrong"): ("過去", "卡住", "問題"),
    ("broke-up-long", "stay-or-let-go"): ("等", "放下", "投入", "時間"),
    ("cold-war", "still-love-me"): ("主動", "聯絡"),
    ("cold-war", "any-chance"): ("冷戰", "變軟", "鬆動", "化開"),
    ("cold-war", "when-to-contact"): ("開口", "壓力", "加分", "扣分"),
    ("cold-war", "what-did-i-do-wrong"): ("冷戰", "沉默", "防衛"),
    ("cold-war", "stay-or-let-go"): ("界線", "停", "等"),
    ("crisis", "still-love-me"): ("繼續", "維持", "關係"),
    ("crisis", "any-chance"): ("修復",),
    ("crisis", "when-to-contact"): ("降低", "衝突", "惡性循環"),
    ("crisis", "what-did-i-do-wrong"): ("爭吵", "循環", "衝突"),
    ("crisis", "stay-or-let-go"): ("修", "傷", "關係"),
}


CORE_DIRECT_ANSWER_CATALOG = {
    ("ambiguous", "still-love-me", "blocked"): "他仍拒絕聯絡時，目前看不到把曖昧認真發展下去的現實條件",
    ("ambiguous", "still-love-me", "no-contact"): "目前沒有新的互動，所以還看不出他是否願意把好感變成認真關係",
    ("ambiguous", "still-love-me", "occasional-contact"): "零星回應表示好感可能還在，但要有持續而主動的靠近才算認真",
    ("ambiguous", "still-love-me", "still-in-contact"): "你們仍有聯絡，只有他也主動安排相處並持續投入，這段曖昧才有走向認真的可能",
    ("ambiguous", "still-love-me", "living-or-working-together"): "共同場合的往來不能代表認真，只有他在必要接觸之外也主動靠近，才值得把它看成關係可能",
    ("ambiguous", "any-chance", "blocked"): "對方仍拒絕聯絡時，這段曖昧目前沒有往關係發展的互動空間",
    ("ambiguous", "any-chance", "no-contact"): "目前沒有新的雙向互動，這段曖昧還看不出會不會往關係發展",
    ("ambiguous", "any-chance", "occasional-contact"): "零星回應保留了一點可能，但要有連續投入和更清楚的意圖才算正在發展",
    ("ambiguous", "any-chance", "still-in-contact"): "你們仍能對話，如果雙方都願意把安排和期待說清楚，關係才可能往前",
    ("ambiguous", "any-chance", "living-or-working-together"): "必要接觸只代表仍會見面，私下也有自發靠近才算關係正在發展",
    ("ambiguous", "when-to-contact", "blocked"): "對方仍拒絕聯絡時，現在不適合再開口要求把曖昧說清楚",
    ("ambiguous", "when-to-contact", "no-contact"): "目前沒有聯絡，如果對方沒有明確拒絕，可以用一則短訊息確認他是否願意把互動說清楚",
    ("ambiguous", "when-to-contact", "occasional-contact"): "零星回應開始穩定後，可以先問一件想法，不要一次要求定義整段關係",
    ("ambiguous", "when-to-contact", "still-in-contact"): "你們自然聊得下去時，可以選平靜的時刻把一個不清楚的地方說開",
    ("ambiguous", "when-to-contact", "living-or-working-together"): "共同場合不適合突然把關係說清楚，先另外確認一個雙方都願意開口的私人時間",
    ("ambiguous", "what-did-i-do-wrong", "blocked"): "他關閉聯絡後看不出完整的忽冷忽熱原因，先不要用追問替空白補答案",
    ("ambiguous", "what-did-i-do-wrong", "no-contact"): "長時間沒有互動時，現在能確認的是他沒有持續靠近，還不能替忽冷忽熱下單一原因",
    ("ambiguous", "what-did-i-do-wrong", "occasional-contact"): "他在你開口時回應、之後又不延續，這種一近一退就是忽冷忽熱的主要節奏",
    ("ambiguous", "what-did-i-do-wrong", "still-in-contact"): "相處沒有壓力時他願意靠近，話題碰到定位或責任時又退開，所以感受才會忽冷忽熱",
    ("ambiguous", "what-did-i-do-wrong", "living-or-working-together"): "共同場合裡的熱絡和私下的距離同時存在，才讓你感到他忽冷忽熱",
    ("ambiguous", "stay-or-let-go", "blocked"): "他仍拒絕聯絡時，這段曖昧已經沒有值得你繼續觀察的新行動",
    ("ambiguous", "stay-or-let-go", "no-contact"): "目前沒有新互動，可以停止主動等待，只有他重新靠近時再評估是否值得觀察",
    ("ambiguous", "stay-or-let-go", "occasional-contact"): "可以再觀察一小段時間，但只有零星回應變成持續主動才值得繼續",
    ("ambiguous", "stay-or-let-go", "still-in-contact"): "你們仍有聯絡，可以繼續觀察他是否也會投入，而不是只看聊天有沒有熱絡",
    ("ambiguous", "stay-or-let-go", "living-or-working-together"): "必要往來不能成為繼續等待的理由，只有私下也有主動靠近才值得觀察",
    ("broke-up-recent", "still-love-me", "blocked"): "他仍拒絕聯絡時，無法確認心裡是否還有你，只能先尊重他現在的界線",
    ("broke-up-recent", "still-love-me", "no-contact"): "分手後沒有新的互動，感情可能還沒完全退去，但目前看不到他願意回來的心意",
    ("broke-up-recent", "still-love-me", "occasional-contact"): "他偶爾回應表示並非完全沒有在意，但還不能當成想復合的心意",
    ("broke-up-recent", "still-love-me", "still-in-contact"): "你們仍有聯絡，代表彼此還會被牽動，但這份心意是否想回到關係要看持續而主動的行動",
    ("broke-up-recent", "still-love-me", "living-or-working-together"): "分手後仍因生活或工作碰面，必要接觸不能直接證明他心裡還想復合",
    ("broke-up-recent", "any-chance", "blocked"): "他仍拒絕聯絡時，現在沒有復合所需的共同互動空間",
    ("broke-up-recent", "any-chance", "no-contact"): "目前沒有新的雙向靠近，所以復合機會還缺少現實支持",
    ("broke-up-recent", "any-chance", "occasional-contact"): "零星回應留下了一點修復空間，但分手原因開始改變才可能談復合",
    ("broke-up-recent", "any-chance", "still-in-contact"): "你們仍能對話，只有雙方不再重複分手前的相處方式，復合才有機會",
    ("broke-up-recent", "any-chance", "living-or-working-together"): "必要往來不等於想復合，只有私下也願意處理分手原因才算出現修復可能",
    ("broke-up-recent", "when-to-contact", "blocked"): "他沒有重新開放聯絡以前，任何時間都不適合主動恢復互動",
    ("broke-up-recent", "when-to-contact", "no-contact"): "如果他沒有明確拒絕，等情緒比較平穩後可以用一則短訊息確認是否能恢復互動",
    ("broke-up-recent", "when-to-contact", "occasional-contact"): "零星回應能穩定延續時，才適合慢慢恢復互動，不要立刻談復合",
    ("broke-up-recent", "when-to-contact", "still-in-contact"): "你們已有對話時，選雙方都平靜的時候處理一個小問題，比追問結果更容易恢復互動",
    ("broke-up-recent", "when-to-contact", "living-or-working-together"): "先另外約一個雙方同意的時間談，才能避免在共同場合把恢復互動變成壓力",
    ("broke-up-recent", "what-did-i-do-wrong", "blocked"): "他關閉聯絡不能證明分手全是你的錯，真正原因仍要回到分手前反覆卡住的互動",
    ("broke-up-recent", "what-did-i-do-wrong", "no-contact"): "目前沒有新對話能核對原因，先回看分手前哪個問題一再失去平衡，不要只剩自責",
    ("broke-up-recent", "what-did-i-do-wrong", "occasional-contact"): "從偶爾的對話裡看哪個話題再次卡住，才能分清分手原因和各自責任",
    ("broke-up-recent", "what-did-i-do-wrong", "still-in-contact"): "你們還能談時，把分手前最後幾次失控拆成具體事件，比追問誰全錯更接近原因",
    ("broke-up-recent", "what-did-i-do-wrong", "living-or-working-together"): "每天碰面造成的小摩擦不等於全部分手原因，必要往來和感情問題要分開看",
    ("broke-up-recent", "stay-or-let-go", "blocked"): "他仍拒絕聯絡時，現在要先把自己穩住，不要把等待放在他的界線上",
    ("broke-up-recent", "stay-or-let-go", "no-contact"): "分手後沒有新互動時，先把自己穩住，只有他重新主動靠近才需要再考慮等待",
    ("broke-up-recent", "stay-or-let-go", "occasional-contact"): "可以保留一點觀察，但先穩住自己的生活，別讓零星回應決定每天的情緒",
    ("broke-up-recent", "stay-or-let-go", "still-in-contact"): "你們仍有聯絡，也要先把自己穩住，再看雙方是否真的改變分手前的問題",
    ("broke-up-recent", "stay-or-let-go", "living-or-working-together"): "即使仍會碰面，也不要把必要接觸當成等待理由，先讓自己的情緒和生活穩下來",
    ("broke-up-long", "still-love-me", "blocked"): "他目前用拒絕聯絡表達距離，除了尊重這個態度，還不能推測他心裡怎麼看你",
    ("broke-up-long", "still-love-me", "no-contact"): "長時間沒有聯絡，表示他目前沒有主動回到關係的態度，不能只用過去推測他怎麼看你",
    ("broke-up-long", "still-love-me", "occasional-contact"): "他仍願意偶爾回應，表示你不是完全被排除，但還看不出他把你放回伴侶位置",
    ("broke-up-long", "still-love-me", "still-in-contact"): "他願意維持聯絡，代表對你仍有回應空間，但要看是否投入更多才能知道現在怎麼看你",
    ("broke-up-long", "still-love-me", "living-or-working-together"): "生活或工作上的正常往來只能說明他願意合作，不能直接代表他仍用感情看待你",
    ("broke-up-long", "any-chance", "blocked"): "聯絡仍被關閉時，這段緣分目前沒有現實延續的入口",
    ("broke-up-long", "any-chance", "no-contact"): "分開一段時間仍沒有新互動，這段關係暫時缺少延續下去的現實條件",
    ("broke-up-long", "any-chance", "occasional-contact"): "少量互動保留一點延續可能，但只有雙方持續靠近才會變成現實",
    ("broke-up-long", "any-chance", "still-in-contact"): "你們仍能互動，如果雙方都願意建立不同於過去的相處方式，關係才有延續空間",
    ("broke-up-long", "any-chance", "living-or-working-together"): "必要往來不能證明緣分正在延續，私下也有新的雙向選擇才算現實可能",
    ("broke-up-long", "when-to-contact", "blocked"): "對方仍拒絕聯絡時，不適合換帳號或換方式重新開口",
    ("broke-up-long", "when-to-contact", "no-contact"): "分開已久又沒有聯絡時，如果沒有明確拒絕，可以用一則不要求回覆的訊息重新開口",
    ("broke-up-long", "when-to-contact", "occasional-contact"): "已有零星回應時，適合從輕鬆而具體的話題重新開口，不要先談回到從前",
    ("broke-up-long", "when-to-contact", "still-in-contact"): "你們仍能說話時，可以直接但簡短地重新開口了解彼此，再讓他的回應決定下一步",
    ("broke-up-long", "when-to-contact", "living-or-working-together"): "生活或工作場合不是重新開口談感情的地方，先詢問他是否願意另外找時間聊",
    ("broke-up-long", "what-did-i-do-wrong", "blocked"): "他現在拒絕聯絡，無法核對過去卡住的互動，也不能把全部問題算在你身上",
    ("broke-up-long", "what-did-i-do-wrong", "no-contact"): "長期沉默後，先回看過去哪種互動總讓一方退開，而不是用最後一次事件解釋全部",
    ("broke-up-long", "what-did-i-do-wrong", "occasional-contact"): "偶爾重新說話時，留意哪種話題又讓對話中斷，那通常就是過去卡住的模式",
    ("broke-up-long", "what-did-i-do-wrong", "still-in-contact"): "你們現在還能談，可以一起指出過去哪個互動反覆失控，避免只翻舊帳",
    ("broke-up-long", "what-did-i-do-wrong", "living-or-working-together"): "共同場合的客氣不能解釋過去問題，要分開看日常合作和當時卡住的感情互動",
    ("broke-up-long", "stay-or-let-go", "blocked"): "他長期沒有重新開放聯絡時，可以慢慢放下，不必繼續替關係保留時間",
    ("broke-up-long", "stay-or-let-go", "no-contact"): "分開已久又沒有新靠近時，等待缺少現實依據，可以把時間慢慢收回自己身上",
    ("broke-up-long", "stay-or-let-go", "occasional-contact"): "偶爾回應還不足以值得繼續等，只有穩定而雙向的投入才需要重新評估",
    ("broke-up-long", "stay-or-let-go", "still-in-contact"): "你們仍有聯絡，可以暫時觀察，但如果只有你在維持，就要慢慢放下等待",
    ("broke-up-long", "stay-or-let-go", "living-or-working-together"): "必要接觸不是繼續等的理由，沒有私下主動靠近時就把投入慢慢收回",
    ("cold-war", "still-love-me", "blocked"): "他仍拒絕聯絡時，目前看不到他會主動開口的跡象",
    ("cold-war", "still-love-me", "no-contact"): "冷戰期間完全沒有新互動，還不能假設他會主動聯絡，只能看他是否自己打破沉默",
    ("cold-war", "still-love-me", "occasional-contact"): "他偶爾回應但沒有主動開場，表示聯絡通道還在，還不算他主動回來",
    ("cold-war", "still-love-me", "still-in-contact"): "你們仍能對話，如果他會自己開啟下一次話題，才算主動聯絡正在恢復",
    ("cold-war", "still-love-me", "living-or-working-together"): "每天碰面不等於主動聯絡，只有他在必要往來之外也來找你才算",
    ("cold-war", "any-chance", "blocked"): "他仍封鎖或拒絕聯絡時，冷戰目前沒有變軟的空間",
    ("cold-war", "any-chance", "no-contact"): "冷戰後沒有任何新互動，只有一方主動打破沉默才可能開始鬆動",
    ("cold-war", "any-chance", "occasional-contact"): "偶爾回應表示冷戰有一點變軟，但要能持續對話才算真正鬆動",
    ("cold-war", "any-chance", "still-in-contact"): "你們仍能說話，若語氣和舊問題都開始改變，冷戰才有機會慢慢化開",
    ("cold-war", "any-chance", "living-or-working-together"): "共同場合能正常相處只是第一步，私下也能自然說話才表示冷戰在變軟",
    ("cold-war", "when-to-contact", "blocked"): "對方拒絕聯絡時，現在開口只會越過界線，不能因為換時間就變成加分",
    ("cold-war", "when-to-contact", "no-contact"): "如果沒有明確拒絕，冷戰後只適合簡短開口一次，沒有回應就停下",
    ("cold-war", "when-to-contact", "occasional-contact"): "他偶爾願意回應時，延續原本話題會比直接談關係更不容易增加壓力",
    ("cold-war", "when-to-contact", "still-in-contact"): "你們還能說話時，平靜地處理一個具體問題會加分，一次追問全部答案容易扣分",
    ("cold-war", "when-to-contact", "living-or-working-together"): "共同場合突然談感情容易增加壓力，先約定私人時間再開口比較合適",
    ("cold-war", "what-did-i-do-wrong", "blocked"): "聯絡被關上時，冷戰卡點無法靠追問解開，先尊重界線才能停止惡化",
    ("cold-war", "what-did-i-do-wrong", "no-contact"): "雙方都等對方先開口，沉默本身就成了冷戰一直卡住的地方",
    ("cold-war", "what-did-i-do-wrong", "occasional-contact"): "只在對方開口後才回應，卻沒有人延續話題，冷戰就會停在半開半關的位置",
    ("cold-war", "what-did-i-do-wrong", "still-in-contact"): "你們能說話卻一碰到核心問題就互相防衛，這是冷戰反覆卡住的主要環節",
    ("cold-war", "what-did-i-do-wrong", "living-or-working-together"): "共同場合維持表面平靜、私下卻不談真正問題，會讓冷戰一直拖著",
    ("cold-war", "stay-or-let-go", "blocked"): "他仍拒絕聯絡時，先停在界線內，不要等著用更多接近換來回應",
    ("cold-war", "stay-or-let-go", "no-contact"): "完全沒有聯絡時，先停下主動追問，把是否打破沉默留給他",
    ("cold-war", "stay-or-let-go", "occasional-contact"): "他偶爾回應卻不主動延續時，可以等他下一次主動，期間不要加大聯絡",
    ("cold-war", "stay-or-let-go", "still-in-contact"): "你們仍能對話，不必完全停下，但要守住界線，不用追問他何時給答案",
    ("cold-war", "stay-or-let-go", "living-or-working-together"): "每天碰面時先守住共同場合的界線，再看他是否會在必要往來之外主動靠近",
    ("crisis", "still-love-me", "blocked"): "即使名義上還在一起，他仍拒絕聯絡時，目前看不到願意共同繼續的行動",
    ("crisis", "still-love-me", "no-contact"): "你們還在關係裡卻長時間沒有聯絡，表示他目前沒有用行動維持這段關係",
    ("crisis", "still-love-me", "occasional-contact"): "他偶爾回應表示還沒有完全退出，但是否想繼續要看他會不會穩定參與",
    ("crisis", "still-love-me", "still-in-contact"): "你們仍有日常聯絡，只有他願意一起處理問題並持續投入，才算真的想繼續",
    ("crisis", "still-love-me", "living-or-working-together"): "共同責任讓你們仍會碰面，但他是否想繼續要看必要往來之外的關係行動",
    ("crisis", "any-chance", "blocked"): "即使還在關係裡，聯絡被關閉時也沒有共同修復的條件",
    ("crisis", "any-chance", "no-contact"): "長時間沒有對話時，關係暫時無法修復，先要恢復基本而安全的溝通",
    ("crisis", "any-chance", "occasional-contact"): "零星對話表示仍有修復入口，但雙方要停止同一種衝突才會有變化",
    ("crisis", "any-chance", "still-in-contact"): "你們仍能說話，只要彼此願意改掉反覆傷人的做法，關係仍有修復空間",
    ("crisis", "any-chance", "living-or-working-together"): "一起生活或工作不能代替修復，只有私下也願意處理衝突才算真正改變",
    ("crisis", "when-to-contact", "blocked"): "對方拒絕聯絡時，降低惡性循環的第一步是停止追問和所有繞路接近",
    ("crisis", "when-to-contact", "no-contact"): "你們長時間沒有對話時，先用一個不要求答案的方式降低壓力，不要直接重啟爭吵",
    ("crisis", "when-to-contact", "occasional-contact"): "只有零星回應時，先讓一次對話平穩結束，比急著解決整段關係更能降低衝突",
    ("crisis", "when-to-contact", "still-in-contact"): "你們仍能說話時，先把一次爭吵縮成一個具體問題，才能降低惡性循環",
    ("crisis", "when-to-contact", "living-or-working-together"): "共同場合出現摩擦時先暫停感情爭論，另外約時間處理，才能避免衝突擴大",
    ("crisis", "what-did-i-do-wrong", "blocked"): "互相封鎖或拒絕聯絡，表示爭吵已從問題本身變成彼此都在防衛的循環",
    ("crisis", "what-did-i-do-wrong", "no-contact"): "爭吵後長時間沉默，代表你們的循環是衝突一升高就切斷對話，問題因此留在原地",
    ("crisis", "what-did-i-do-wrong", "occasional-contact"): "每次只短暫恢復對話又因同一件事中斷，這就是反覆爭吵沒有真正修復的模式",
    ("crisis", "what-did-i-do-wrong", "still-in-contact"): "你們一想把問題說清楚就互相提高力道，沒有人先停下來，所以爭吵會被反覆推高",
    ("crisis", "what-did-i-do-wrong", "living-or-working-together"): "共同生活或工作中的小摩擦不斷帶回感情舊帳，讓同一個爭吵循環一直重演",
    ("crisis", "stay-or-let-go", "blocked"): "即使還在關係裡，對方持續拒絕聯絡也表示目前傷害太重，先停止追趕而不是勉強修復",
    ("crisis", "stay-or-let-go", "no-contact"): "關係裡長時間沒有基本對話時，先把安全和界線放回來，再判斷是否還能修",
    ("crisis", "stay-or-let-go", "occasional-contact"): "只有零星回應時，先看衝突能否停止重演，再決定這段關係是否值得繼續修",
    ("crisis", "stay-or-let-go", "still-in-contact"): "你們仍能對話，關係還有修復空間，但前提是雙方都停止重複傷人的做法",
    ("crisis", "stay-or-let-go", "living-or-working-together"): "仍需共同生活或工作不等於關係已修好，只有衝突在必要往來之外也能下降才值得繼續",
}


def direct_answer(question: str, stage: str, contact: str) -> str:
    identity = (stage, question, contact)
    text = CORE_DIRECT_ANSWER_CATALOG.get(identity)
    if text is None:
        raise FinalNarrativeSemanticCoverageError(
            f"core-answer: unsupported direct-answer context: {identity}"
        )
    focus_terms = CORE_QUESTION_FOCUS_TERMS[(stage, question)]
    if not any(term in text for term in focus_terms):
        raise CoreAnswerNativeChineseError(
            f"core-answer direct answer lost status-question focus: {identity}"
        )
    return text

MEANING_OPTIONS = {
    "still-love-me": (
        "有沒有感覺只能當起點，持續行動才比較能說明他的心意",
        "真正能回答你的，是他會不會主動把互動延續下去",
        "一句回覆不夠，連續而自發的靠近才有判斷價值",
    ),
    "any-chance": (
        "修復不是重新聊天就算成功，而是原本的相處問題開始改變",
        "有機會不等於一定復合，要看雙方能不能改掉舊的相處方式",
        "關係能不能重來，取決於靠近後是否還會重複同樣的傷",
    ),
    "when-to-contact": (
        "適合聯絡的時機，先看對方目前接受多少互動",
        "日期不是唯一重點，現有界線和回應方式更重要",
        "能不能開口，要先看這次聯絡會不會增加壓力",
    ),
    "what-did-i-do-wrong": (
        "與其把錯全攬在自己身上，更重要的是看懂哪個環節反覆失控",
        "你可以調整自己的做法，但不需要替兩個人的選擇負全責",
        "問題通常出在反應互相推高，不是某一句話就能解釋全部",
    ),
    "stay-or-let-go": (
        "捨不得和值得等待要分開，後者需要對方也有實際行動",
        "等待是否值得，要看你得到的是持續回應，還是只有反覆消耗",
        "不用逼自己立刻放下，但要讓現實變化決定你等多久",
    ),
}

UNCERTAINTY_COPY = {
    "low": (
        "目前幾個重要反應大致指向同一方向，仍要讓後續行動繼續確認",
        "現在可以先採用這個判斷，但不能把它當成不會改變的最後答案",
        "現有線索較一致，真正結果仍要由接下來一段時間的選擇證明",
        "目前的反應方向已經比較清楚，但還需要看它能不能持續",
        "現在的證據大致一致，後續如果沒有相同行動，判斷也要跟著調整",
        "這個方向目前有較多實際支持，仍不適合把它說成已經定案",
        "你可以先用這個判斷安排下一步，但要保留對方之後改變選擇的可能",
        "幾個關鍵線索目前指向相同結論，時間拉長後是否仍一致才是最後驗證",
        "這不是只靠一次反應得出的判斷，但仍需要新行動繼續支持",
        "現在可以較有把握地看待這個方向，但不能用它替對方預先承諾",
        "目前的判斷有足夠支持，真正能不能定下來仍要看後續是否一致",
    ),
    "medium": (
        "目前有支持也有保留，不能只挑對自己有利的反應解讀",
        "現在的線索並不完全一致，需要把期待和保留一起看",
        "有些地方支持這個方向，有些部分仍需要後續互動確認",
        "目前的反應有進有退，只看其中一面都容易誤判",
        "這個答案有一些依據，但還沒有多到可以忽略相反的反應",
        "現實線索還在搖擺，需要再看幾次互動才能判定方向",
        "現在不適合把希望或失望任何一邊當成全部答案",
        "部分反應值得留意，但對方是否會持續仍是未確定的地方",
        "你可以保留可能性，同時也要把沒有後續的反應算進判斷",
        "這個方向還沒有穩定到能下結論，新的實際回應仍會改變答案",
        "現在還需要同時容納兩種可能，等之後的行動讓其中一個方向變得更清楚",
    ),
    "high": (
        "目前資訊不足，答案需要保留，不適合替對方下內心結論",
        "現有線索還不足以把答案說滿，先不要用希望補上空白",
        "目前只能停在較保守的判斷，沒有新行動以前不往下推論",
        "現在能看見的反應太少，不足以猜測對方已經做了什麼決定",
        "目前的空白比證據多，任何明確答案都會超過現有資訊",
        "沒有新的實際互動時，現在最負責的做法是保留未知",
        "這個問題還沒有足夠反應可以驗證，不適合把沉默解讀成特定意思",
        "目前不論說得樂觀或悲觀都太早，需要等實際行動出現",
        "現有資訊只能支持一個保守範圍，還不能支持對心意或結果的判定",
        "現在沒有足夠連續性，不能因為單次反應就把答案補完",
        "這個答案需要等新事實出現，不能只用過去的感情做推論",
        "可以判斷的資訊仍太少，在新的實際反應出現前先不定案",
    ),
    "unknown": (
        "目前無法確認答案有多穩，只能先回到看得見的互動",
        "現有資料不足以評估答案是否穩定，需要保留沒有證據的部分",
        "目前不能判定這個方向有多可靠，新的實際反應出現後再調整",
        "這個答案目前沒有可驗證的穩定度，先不繼續往下推論",
        "資料還無法支持明確結論，只保留已經發生的反應",
        "現在的判斷基礎不足，需要等新互動補上缺少的部分",
        "目前不知道這個方向會不會持續，不適合作為最後答案",
        "還沒有足夠線索判定可靠程度，新行動出現前先保留",
        "現有資訊不能說明這個答案有多穩，不用猜測補足它",
        "目前只能回到對方實際做了什麼，其他部分仍是未知",
        "還沒有可以評估穩定度的資料，先把未知保留在答案裡",
    ),
}

CORE_DYNAMIC_EXTRA = {
    "unknown": (
        "目前還不能確定哪個互動問題最影響這個答案",
        "關鍵相處問題仍不清楚，不適合用通用模式補上空白",
        "這題還缺少能指出主要卡點的線索，答案只能先保留",
    ),
    "communication-repair": (
        "你們的答案常卡在重要話題能不能真正說清楚",
        "誤會出現後能否重新聽懂彼此，會直接改變關係方向",
        "只有兩個人都願意聽完，原本的誤會才不會一直重演",
    ),
    "outer-intensity": (
        "感受很強不等於結果已經確定，後續行動才能把兩者分開",
        "這段關係容易用強烈感受填補空白，答案仍要回到現實選擇",
        "牽掛可以很深，但這題仍要由對方現在做了什麼來回答",
    ),
    "identity-rhythm": (
        "是否覺得被尊重，會明顯影響彼此願不願意繼續往前",
        "只要一方覺得被否定，就會先保護自己，原本的問題反而談不下去",
        "只要彼此仍把不同意聽成否定，這個答案就很難真正改變",
    ),
    "emotional-safety": (
        "安全感有沒有恢復，比單次親近更能說明關係現況",
        "小反應一直被解讀成拒絕時，這個答案就很難真正改變",
        "彼此不再一開口就防備，原本的問題才有機會鬆開",
    ),
    "saturn-pressure": (
        "一談到責任或承諾，他就容易變得保守，回應也會慢下來",
        "這個答案會受到現實負擔和界線影響，不能只看感覺",
        "未來和責任仍讓他退開時，現在還不能把感情當成承諾",
    ),
    "action-conflict": (
        "只要你們一著急就互相對抗，同樣的爭執就會再次出現",
        "只要你們願意放慢處理問題的速度，同樣的爭執才有機會停下來",
        "如果每次想解決都變成爭執，現在還看不到新的改變",
    ),
    "attraction-pursuit": (
        "你們容易在有感覺時快速靠近，熱絡結束後誰還會主動才更重要",
        "好感不難出現，真正要看的是之後有沒有繼續靠近",
        "當下有感覺不難，熱度退下後還有沒有主動行動才是關鍵",
        "靠近時有沒有感覺不是重點，熱度過後他是否繼續行動才重要",
        "真正要看的不是一次親近，而是之後有沒有持續靠近",
        "吸引能讓你們重新靠近，但關係要靠後續主動才能往前",
        "彼此被吸引是一回事，熱絡過後還願不願意安排下次見面更重要",
        "不能只看有沒有火花，還要看靠近之後是否有雙方都願意做的事",
        "一時主動只能說明當下有感覺，之後能不能持續才更重要",
        "再次心動不是改變，兩個人把靠近延續到日常才算真正不同",
    ),
    "jupiter-support": (
        "彼此的鼓勵只有變成時間和實際幫助時，才會改變答案",
        "對未來有好的想像還不夠，是否願意真的投入才有判斷價值",
        "這題要看的不是彼此說過什麼期待，而是答應的事有沒有完成",
    ),
    "slow-safety": (
        "可預期的小互動有沒有持續，會比一次熱絡更能改變答案",
        "這段關係需要從穩定節奏累積信任，突然加快反而容易後退",
        "只有幾次穩定而自然的互動累積起來，這個答案才會慢慢改變",
    ),
}


def core_dynamic_variants(value_key: str) -> tuple[str, ...]:
    forms = DYNAMIC_FORMS[value_key]
    return (forms.direct, forms.situational, forms.relational, *CORE_DYNAMIC_EXTRA[value_key])


def core_page_dynamic_variants(value_key: str) -> tuple[str, ...]:
    """Return answer-focused forms that do not restate relationship-fit copy."""

    return CORE_DYNAMIC_EXTRA[value_key]


CORE_PARAGRAPH_DYNAMIC_THESES = {
    "unknown": "目前還看不出哪一種相處問題最常重複",
    "communication-repair": "你們最容易卡在誤會之後，兩個人都急著解釋，卻沒有先確認對方聽見什麼",
    "outer-intensity": "你們最容易把強烈感受當成關係會繼續的證明，距離一拉開又會用猜測補上空白",
    "identity-rhythm": "你們最容易在覺得不被尊重時先保護自己，話題也會從事件變成彼此的對錯",
    "emotional-safety": "你們最容易在回應不明確時開始猜測，一方退開會讓另一方更不安",
    "saturn-pressure": "你們最容易卡在責任和未來，話題一變重，回應也會跟著變慢",
    "action-conflict": "你們最容易卡在處理問題的速度",
    "attraction-pursuit": "你們不缺快速靠近的火花，真正要看的是熱度過後還有沒有雙方行動",
    "jupiter-support": "你們很容易看見彼此的可能性，真正要看的是鼓勵能不能變成日常支持",
    "slow-safety": "你們需要在穩定的小互動裡累積信任，突然加快反而容易讓其中一方退開",
}


CORE_SOFT_SIGNAL_FORBIDDEN = (
    "受傷",
    "反駁",
    "壓力",
    "反擊",
    "失望",
    "負擔",
    "拉開距離",
    "補上空白",
    "提高防備",
    "不安放大",
)

CORE_ATTRACTION_STEMS = {
    ("sun", "moon"): "{actor}坦白做自己時，{receiver}的情緒很容易被帶動",
    ("moon", "sun"): "{actor}說出感受時，{receiver}會立刻注意到{actor_possessive}情緒",
    ("sun", "venus"): "{actor}展現原本的樣子時，{receiver}很容易產生欣賞",
    ("venus", "sun"): "{actor}表達欣賞時，{receiver}會明顯感到被肯定",
    ("sun", "mars"): "{actor}表現得很直接時，{receiver}會更想主動靠近",
    ("mars", "sun"): "{actor}主動靠近時，{receiver}會明顯注意到這份心意",
    ("venus", "mars"): "{actor}表達好感時，{receiver}會更想採取行動",
    ("mars", "venus"): "{actor}主動靠近時，{receiver}很容易被吸引",
    ("moon", "venus"): "{actor}流露情緒時，{receiver}會自然回以關心",
    ("venus", "moon"): "{actor}表達在意時，{receiver}容易感到安心",
    ("moon", "moon"): "{actor}情緒有變化時，{receiver}通常很快就會察覺",
    ("venus", "venus"): "{actor}表達喜歡時，{receiver}通常能接收到其中的好意",
}

CORE_HARD_FRICTION_STEMS = {
    ("mercury", "mars"): "{actor}越急著說清楚，{receiver}越容易馬上反駁",
    ("mars", "mercury"): "{actor}一急著把話說清楚，{receiver}就會開始解釋每個細節",
    ("mercury", "moon"): "{actor}一直講道理時，{receiver}會先被口氣刺到",
    ("moon", "mercury"): "{actor}情緒一上來，{receiver}就很難整理想說的話",
    ("mercury", "sun"): "{actor}指出問題時，{receiver}很容易把它聽成整個人被否定",
    ("sun", "mercury"): "{actor}堅持立場時，{receiver}會用更多理由回應",
    ("mercury", "venus"): "{actor}急著講清楚時，{receiver}會更在意語氣",
    ("venus", "mercury"): "{actor}先照顧氣氛時，{receiver}會覺得問題還沒說清楚",
    ("mercury", "saturn"): "{actor}想一次說完整時，{receiver}會先想到責任和後果",
    ("saturn", "mercury"): "{actor}提出要求時，{receiver}會開始小心每一句話",
    ("mercury", "mercury"): "{actor}照自己的理解解釋時，{receiver}常會聽成另一個意思",
    ("mars", "mars"): "{actor}加快處理速度時，{receiver}也會立刻加大反應",
    ("mars", "saturn"): "{actor}想趕快往前時，{receiver}會先停下來衡量後果",
    ("saturn", "mars"): "{actor}要求先訂界線時，{receiver}會覺得自己被擋住",
    ("moon", "mars"): "{actor}感到受傷時，{receiver}常會馬上用行動或脾氣回應",
    ("mars", "moon"): "{actor}反應太直接時，{receiver}會先感到受傷",
    ("moon", "moon"): "{actor}想立刻得到安慰時，{receiver}可能正想先冷靜",
    ("moon", "venus"): "{actor}期待被照顧時，{receiver}可能不知道怎麼做才對",
    ("venus", "moon"): "{actor}表達好感時，{receiver}未必會把它感受成照顧",
    ("moon", "saturn"): "{actor}需要安慰時，{receiver}會先沉默或講道理",
    ("saturn", "moon"): "{actor}先談現實時，{receiver}會覺得感受被放到後面",
    ("venus", "mars"): "{actor}表達好感時，{receiver}可能回得太快、太直接",
    ("mars", "venus"): "{actor}主動靠近時，{receiver}可能先感到壓力",
    ("venus", "venus"): "{actor}照自己的方式示好時，{receiver}未必能理解",
    ("venus", "saturn"): "{actor}想確認被珍惜時，{receiver}會先想到現實限制",
    ("saturn", "venus"): "{actor}先談責任時，{receiver}會把好感收得更保守",
    ("sun", "saturn"): "{actor}想照自己的方式做決定時，{receiver}會先提出限制",
    ("saturn", "sun"): "{actor}提出要求時，{receiver}很容易覺得自己做得不夠",
    ("sun", "moon"): "{actor}照自己的方式決定時，{receiver}的感受容易被忽略",
    ("moon", "sun"): "{actor}想得到情緒回應時，{receiver}可能還在堅持自己的做法",
    ("sun", "venus"): "{actor}照自己的方式表達時，{receiver}未必感受到好意",
    ("venus", "sun"): "{actor}表達欣賞時，{receiver}仍可能覺得自己沒被理解",
    ("sun", "mars"): "{actor}想主導方向時，{receiver}容易立刻用行動反駁",
    ("mars", "sun"): "{actor}直接採取行動時，{receiver}會覺得自己的想法被壓過",
}

CORE_GROWTH_STEMS = {
    ("mars", "saturn"): "{actor}先放慢速度，{receiver}才比較能說出界線",
    ("saturn", "mars"): "{actor}把界線和時間說清楚，{receiver}才知道下一步怎麼做",
    ("moon", "saturn"): "{actor}直接說需要什麼安慰，{receiver}才知道怎麼陪伴",
    ("saturn", "moon"): "{actor}先回應感受再談現實，{receiver}就不需要一直確認",
    ("sun", "saturn"): "{actor}把期待拆成做得到的小事，{receiver}就比較敢承擔",
    ("saturn", "sun"): "{actor}談要求前先肯定{receiver}做過的努力，{receiver}就不會立刻覺得被否定",
    ("venus", "saturn"): "{actor}用持續的小行動示好，{receiver}會比較安心",
    ("saturn", "venus"): "{actor}只承諾能做到的事，{receiver}才比較敢表達好感",
    ("mercury", "saturn"): "{actor}先約好這次只談什麼，{receiver}比較能把話說完",
    ("saturn", "mercury"): "{actor}把要求說具體而且不帶批評，{receiver}比較願意繼續談",
}

CORE_SOFT_FRICTION_STEMS = {
    ("mercury", "mars"): "{actor}急著把話說清楚時，{receiver}的回應速度也會跟著變快",
    ("mars", "mercury"): "{actor}把想法直接說出來時，{receiver}通常願意把細節說明白",
    ("mercury", "moon"): "{actor}專心說明道理時，{receiver}會先留意語氣和感受",
    ("moon", "mercury"): "{actor}情緒一上來，{receiver}需要更多時間整理想說的話",
    ("mercury", "sun"): "{actor}指出問題時，{receiver}會特別在意自己是否被否定",
    ("sun", "mercury"): "{actor}堅持自己的立場時，{receiver}會想用理由把差異說清楚",
    ("mercury", "venus"): "{actor}急著講清楚時，{receiver}也會留意口氣和感受",
    ("venus", "mercury"): "{actor}先顧及氣氛時，{receiver}會想確認問題有沒有說清楚",
    ("mercury", "saturn"): "{actor}想把話說完整時，{receiver}會先確認責任、規則或後果",
    ("saturn", "mercury"): "{actor}提出標準或責任時，{receiver}會更仔細選擇說法",
    ("mercury", "mercury"): "{actor}用自己的方式解釋時，{receiver}可能先從另一個角度理解",
    ("mars", "mars"): "{actor}想按自己的速度處理時，{receiver}也會很快做出回應",
    ("mars", "saturn"): "{actor}想加快進度時，{receiver}會先確認自己能不能承擔",
    ("saturn", "mars"): "{actor}要求先確認界線時，{receiver}會先調整自己的行動",
    ("moon", "mars"): "{actor}情緒被碰到時，{receiver}會很快做出回應",
    ("mars", "moon"): "{actor}反應很直接時，{receiver}會先注意{actor_possessive}語氣和態度",
    ("moon", "moon"): "{actor}想靠近尋求安慰時，{receiver}也會留意自己的感受",
    ("moon", "venus"): "{actor}期待被照顧時，{receiver}會想用自己的方式關心",
    ("venus", "moon"): "{actor}用自己的方式示好時，{receiver}會先確認自己是否感到安心",
    ("moon", "saturn"): "{actor}需要安慰時，{receiver}會先想自己能怎麼陪伴",
    ("saturn", "moon"): "{actor}先談責任和現實時，{receiver}也需要確認自己的感受被理解",
    ("venus", "mars"): "{actor}表達好感時，{receiver}會更想直接回應",
    ("mars", "venus"): "{actor}主動靠近時，{receiver}會先留意自己是否舒服",
    ("venus", "venus"): "{actor}用自己的方式示好時，{receiver}也會用自己的方式理解",
    ("venus", "saturn"): "{actor}想確認被珍惜時，{receiver}會先考慮自己能不能穩定做到",
    ("saturn", "venus"): "{actor}先談責任或界線時，{receiver}會先確認自己能怎麼表達好感",
    ("sun", "saturn"): "{actor}照自己的方式做決定時，{receiver}會先想哪些事能穩定做到",
    ("saturn", "sun"): "{actor}提出責任和要求時，{receiver}會特別在意自己的努力是否被肯定",
    ("sun", "moon"): "{actor}照自己的方式做決定時，{receiver}會先確認自己的感受",
    ("moon", "sun"): "{actor}需要情緒回應時，{receiver}會先想自己能怎麼回應",
    ("sun", "venus"): "{actor}照自己的方式表達時，{receiver}會用自己的方式感受其中的好意",
    ("venus", "sun"): "{actor}表達欣賞時，{receiver}會特別在意自己是否真的被看見",
    ("sun", "mars"): "{actor}想主導方向時，{receiver}會更想用行動回應",
    ("mars", "sun"): "{actor}直接採取行動時，{receiver}會先確認自己的想法有沒有被聽見",
}

CORE_SOFT_OUTER_ACTOR_ACTIONS = {
    "uranus": "調整彼此距離",
    "neptune": "表達對關係的想像",
    "pluto": "表現出強烈在意",
    "outer": "帶出強烈感受",
}
CORE_SOFT_PERSONAL_ACTIONS = {
    "sun": "說出自己的立場",
    "moon": "表達當下感受",
    "mercury": "解釋自己的想法",
    "venus": "讓對方知道自己的好感",
    "mars": "直接採取行動",
    "jupiter": "說起兩個人的未來",
    "saturn": "要求確認責任或界線",
}
CORE_SOFT_PERSONAL_TARGETS = {
    "sun": "自我肯定",
    "moon": "情緒",
    "mercury": "想法",
    "venus": "好感",
    "mars": "行動節奏",
    "jupiter": "期待",
    "saturn": "責任感",
}
CORE_SOFT_OUTER_RESPONSES = {
    "uranus": "會更留意彼此需要多少空間",
    "neptune": "會更容易理解其中的期待",
    "pluto": "會更明顯感受到這份在意",
    "outer": "會更明顯感受到其中的分量",
}
CORE_HARD_OUTER_ACTOR_ACTIONS = {
    "uranus": "一下靠近、一下退開",
    "neptune": "用猜測填補沒有說清楚的地方",
    "pluto": "把在意表現得很強",
    "outer": "讓情緒變得更強烈",
}
CORE_HARD_OUTER_RESPONSES = {
    "uranus": "會一下靠近、一下退開",
    "neptune": "會用猜測補上沒有說清楚的部分",
    "pluto": "會更在意並想保護自己",
    "outer": "會讓原本的感受越來越強",
}


def core_soft_outer_stem(signal: RelationshipSignal) -> str:
    actor = "你" if signal.actor_person == "persona" else "他"
    receiver = "你" if signal.receiver_person == "persona" else "他"
    if signal.actor_planet in OUTER_PLANETS:
        action = CORE_SOFT_OUTER_ACTOR_ACTIONS[signal.actor_planet]
        if signal.receiver_planet in OUTER_PLANETS:
            response = CORE_SOFT_OUTER_RESPONSES[signal.receiver_planet]
            return f"{actor}{action}時，{receiver}{response}"
        target = CORE_SOFT_PERSONAL_TARGETS[signal.receiver_planet]
        return f"{actor}{action}時，{receiver}會更明顯感受到自己的{target}"
    action = CORE_SOFT_PERSONAL_ACTIONS[signal.actor_planet]
    response = CORE_SOFT_OUTER_RESPONSES[signal.receiver_planet]
    return f"{actor}{action}時，{receiver}{response}"


def core_hard_outer_stem(signal: RelationshipSignal) -> str:
    actor = "你" if signal.actor_person == "persona" else "他"
    receiver = "你" if signal.receiver_person == "persona" else "他"
    if signal.actor_planet in OUTER_PLANETS:
        action = CORE_HARD_OUTER_ACTOR_ACTIONS[signal.actor_planet]
        if signal.receiver_planet in OUTER_PLANETS:
            response = CORE_HARD_OUTER_RESPONSES[signal.receiver_planet]
            return f"{actor}{action}時，{receiver}{response}"
        target = CORE_SOFT_PERSONAL_TARGETS[signal.receiver_planet]
        return f"{actor}{action}時，{receiver}原本的{target}很容易被打亂"
    action = CORE_SOFT_PERSONAL_ACTIONS[signal.actor_planet]
    response = CORE_HARD_OUTER_RESPONSES[signal.receiver_planet]
    return f"{actor}{action}時，{receiver}{response}"


def core_pair_stem(
    signal: RelationshipSignal,
    templates: Mapping[tuple[str, str], str],
) -> str:
    template = templates.get((signal.actor_planet, signal.receiver_planet))
    if template is None:
        raise CoreAnswerNativeChineseError(
            f"unsupported core {signal.kind} signal direction: "
            f"{signal.actor_planet}>{signal.receiver_planet}"
        )
    actor = "你" if signal.actor_person == "persona" else "他"
    receiver = "你" if signal.receiver_person == "persona" else "他"
    return template.format(
        actor=actor,
        receiver=receiver,
        actor_possessive="你的" if signal.actor_person == "persona" else "他的",
        receiver_possessive="你的" if signal.receiver_person == "persona" else "他的",
    )


def core_signal_stem(signal: RelationshipSignal) -> str:
    if signal.pair_key == "outer-planet-intensity":
        if signal.aspect in {"sextile", "trine"}:
            return core_soft_outer_stem(signal)
        return core_hard_outer_stem(signal)
    if signal.kind == "attraction":
        return core_pair_stem(signal, CORE_ATTRACTION_STEMS)
    if signal.kind == "growth":
        return core_pair_stem(signal, CORE_GROWTH_STEMS)
    if signal.aspect in {"sextile", "trine"}:
        return core_pair_stem(signal, CORE_SOFT_FRICTION_STEMS)
    return core_pair_stem(signal, CORE_HARD_FRICTION_STEMS)

CORE_SIGNAL_ENDINGS = {
    "attraction": {
        "direct": {
            "conjunction": "，彼此的反應來得又快又明顯",
            "sextile": "，彼此通常願意自然靠近",
            "trine": "，好感比較容易留在日常",
            "square": "，吸引和敏感會一起放大",
            "opposition": "，靠近時也容易拉扯",
            "quincunx": "，彼此有反應，表達方式卻常常對不上",
        },
        "situational": {
            "conjunction": "，互動一開始就容易升溫",
            "sextile": "，氣氛放鬆時容易接近",
            "trine": "，相處時不太需要刻意試探",
            "square": "，越在意越容易碰到敏感點",
            "opposition": "，一靠近又可能想退開",
            "quincunx": "，靠近後才發現步調不同",
        },
        "relational": {
            "conjunction": "，你們的互動很快就會升溫",
            "sextile": "，你們通常願意為靠近多走一步",
            "trine": "，你們容易在日常裡累積好感",
            "square": "，你們越靠近，彼此越容易敏感",
            "opposition": "，你們互相吸引，也容易保持距離",
            "quincunx": "，你們有好感，接近方式卻常對不上",
        },
    },
    "friction": {
        "direct": {
            "conjunction": "，原本的小事也容易被放大",
            "sextile": "，停下來確認通常還能說開",
            "trine": "，彼此多半能自然換一種做法",
            "square": "，兩邊很快就會互相頂住",
            "opposition": "，雙方容易站到相反位置",
            "quincunx": "，談得越久越容易錯開重點",
        },
        "situational": {
            "conjunction": "，壓力一高，原本的小事就會被放大",
            "sextile": "，願意停一下時仍能重新聽懂",
            "trine": "，出現分歧時仍有調整空間",
            "square": "，一著急，對話就容易變硬",
            "opposition": "，越想說服，彼此越難靠近",
            "quincunx": "，兩邊常在不同重點上努力",
        },
        "relational": {
            "conjunction": "，兩個人的壓力會一起升高",
            "sextile": "，你們看得見差異，也有機會調整",
            "trine": "，你們通常能在衝突前換一種做法",
            "square": "，你們越想解決，越容易互相防備",
            "opposition": "，你們常用相反方式保護自己",
            "quincunx": "，你們常覺得對方沒有聽懂重點",
        },
    },
    "growth": {
        "direct": {
            "conjunction": "，這個調整有沒有用，很快就會看出來",
            "sextile": "，兩個人比較容易真的做出改變",
            "trine": "，新的做法比較容易留在日常",
            "square": "，需要刻意練習才不會回到舊問題",
            "opposition": "，兩邊都要改，不能只靠一方退讓",
            "quincunx": "，做法需要幾次修正才會對上",
        },
        "situational": {
            "conjunction": "，相處方式會不會不同，很快就會看出來",
            "sextile": "，先從一件小事開始比較做得到",
            "trine": "，持續幾次後會變得更自然",
            "square": "，壓力一高仍可能回到舊方法",
            "opposition": "，雙方都參與才不會變成單方面配合",
            "quincunx": "，每次修正一點才容易找到節奏",
        },
        "relational": {
            "conjunction": "，你們很快就能看出改變是否有效",
            "sextile": "，你們比較容易把它變成共同習慣",
            "trine": "，你們能用小改變慢慢累積信任",
            "square": "，你們要一起練習才不會回到衝突",
            "opposition": "，你們都要參與，不能只讓一個人改",
            "quincunx": "，你們需要反覆調整才能找到合適做法",
        },
    },
}


def core_signal_forms(value_key: str) -> RealizationForms:
    signal = resolve_relationship_signal(value_key)
    stem = core_signal_stem(signal)
    endings = CORE_SIGNAL_ENDINGS[signal.kind]
    return RealizationForms(
        stem + endings["direct"][signal.aspect],
        stem + endings["situational"][signal.aspect],
        stem + endings["relational"][signal.aspect],
    )


def core_evidence_variants(value_key: str) -> tuple[str, ...]:
    forms = core_signal_forms(value_key)
    return (forms.direct, forms.situational, forms.relational)

CORE_UNKNOWN_EVIDENCE = "目前沒有足夠的合盤線索指出最關鍵的互動證據"
CORE_UNKNOWN_EVIDENCE_BY_QUESTION = {
    "still-love-me": "目前看得出你們會互相牽動，但還不能只靠這點判斷他的心意",
    "any-chance": "目前看得出你們仍會互相牽動，但能不能重來要看舊問題是否改變",
    "when-to-contact": "目前的星盤只能說明你們容易在哪裡互相影響，不能替你決定現在是否適合聯絡",
    "what-did-i-do-wrong": "目前沒有一個星盤位置能把原因全放在你身上，仍要回到具體事件",
    "stay-or-let-go": "目前的星盤不能單獨支持你繼續等待，仍要看他現在有沒有實際靠近",
}
CORE_ANSWER_FORBIDDEN_REGRESSIONS = (
    "你的靠近和處理衝突的速度",
    "他的表達好感的方式",
    "一明顯，也會被帶動",
    "會牽動你的",
    "會牽動他的",
)


def single_fact(facts: SectionFactReader, role: str) -> dict[str, Any]:
    records = facts.records(role)
    if len(records) != 1:
        raise FinalNarrativeSemanticCoverageError(
            f"{facts.section_id}: expected one {role} fact, got {len(records)}"
        )
    return records[0]


def selected_track(question: str, tracks: list[str]) -> str:
    for track in tracks:
        require_supported_value(
            section_id="core-answer",
            role="answer-track",
            value=track,
            supported=set(ANSWER_TRACK_HEADLINES),
        )
    priorities = QUESTION_TRACK_PRIORITY[question]
    return next((track for track in priorities if track in tracks), tracks[0])


def context_index(question: str, stage: str, contact: str) -> int:
    return (
        domain_index(question, QUESTION_KEYS, identity="core-answer:question") * 25
        + domain_index(stage, RELATIONSHIP_STAGE_KEYS, identity="core-answer:relationship-stage") * 5
        + domain_index(contact, CONTACT_STATUS_KEYS, identity="core-answer:contact-status")
    )


def render_core_answer(facts: SectionFactReader, seed: str) -> dict[str, str]:
    del seed
    question_fact = single_fact(facts, "question")
    stage_fact = single_fact(facts, "relationship-stage")
    contact_fact = single_fact(facts, "contact-status")
    track_facts = facts.records("answer-track")
    dynamic_fact = single_fact(facts, "central-dynamic")
    partner_fact = single_fact(facts, "partner-relationship-need")
    evidence_fact = single_fact(facts, "evidence-signal")
    observable_fact = single_fact(facts, "observable-sign")
    uncertainty_fact = single_fact(facts, "uncertainty-level")

    question = str(question_fact.get("valueKey") or "")
    stage = str(stage_fact.get("valueKey") or "")
    contact = str(contact_fact.get("valueKey") or "")
    tracks = [str(item.get("valueKey") or "") for item in track_facts]
    dynamic = str(dynamic_fact.get("valueKey") or "")
    partner_need_key = str(partner_fact.get("valueKey") or "")
    evidence_value = str(evidence_fact.get("valueKey") or "")
    observable = str(observable_fact.get("valueKey") or "")
    uncertainty = str(uncertainty_fact.get("valueKey") or "")

    require_supported_value(section_id=facts.section_id, role="question", value=question, supported=QUESTION_KEYS)
    require_supported_value(
        section_id=facts.section_id,
        role="relationship-stage",
        value=stage,
        supported=RELATIONSHIP_STAGE_KEYS,
    )
    require_supported_value(
        section_id=facts.section_id,
        role="contact-status",
        value=contact,
        supported=CONTACT_STATUS_KEYS,
    )
    require_supported_value(
        section_id=facts.section_id,
        role="central-dynamic",
        value=dynamic,
        supported={*RELATIONSHIP_DYNAMIC_KEYS, "unknown"},
    )
    require_supported_value(
        section_id=facts.section_id,
        role="uncertainty-level",
        value=uncertainty,
        supported=set(UNCERTAINTY_COPY),
    )
    if not tracks:
        raise FinalNarrativeSemanticCoverageError("core-answer: required answer-track facts are missing")
    track = selected_track(question, tracks)

    partner_sign = sign_name(partner_need_key)
    require_supported_value(
        section_id=facts.section_id,
        role="partner-relationship-need",
        value=partner_sign,
        supported={*ZODIAC_SIGNS, "unknown"},
    )
    if partner_sign == "unknown":
        facts.record_unknown_fallback(
            "partner-relationship-need",
            partner_sign,
            "partner-relationship-need-unknown",
        )
    if dynamic == "unknown":
        facts.record_unknown_fallback(
            "central-dynamic",
            dynamic,
            "central-dynamic-unknown",
        )
    if uncertainty == "unknown":
        facts.record_unknown_fallback(
            "uncertainty-level",
            uncertainty,
            "uncertainty-level-unknown",
        )
    evidence_purpose = "relational"
    if is_unknown_signal(evidence_value):
        evidence_purpose = "direct"
        facts.record_unknown_fallback(
            "evidence-signal",
            evidence_value,
            "core-evidence-unresolved",
        )
        evidence_copy = CORE_UNKNOWN_EVIDENCE_BY_QUESTION[question]
    else:
        try:
            evidence_copy = core_signal_forms(evidence_value).for_purpose(
                evidence_purpose
            )
        except ValueError as exc:
            raise FinalNarrativeSemanticCoverageError(
                f"core-answer:evidence-signal: unsupported value: {evidence_value}"
            ) from exc

    require_supported_value(
        section_id=facts.section_id,
        role="observable-sign",
        value=observable,
        supported=set(OBSERVABLE_FORMS),
    )
    observable_purpose = "direct"
    change_condition = realize(
        OBSERVABLE_FORMS,
        observable,
        observable_purpose,
        identity="core-answer:observable-sign",
    )

    headline = ANSWER_TRACK_HEADLINES[track]
    meaning = direct_answer(question, stage, contact)
    caution = UNCERTAINTY_COPY[uncertainty][0]
    rendered = {
        "headline": headline,
        "meaning": join_sentences(meaning),
        "body": join_sentences(evidence_copy),
        "nextMove": join_sentences(change_condition),
        "caution": join_sentences(caution),
    }
    frames = {
        "track": frame_from_fact(
            next(item for item in track_facts if item.get("valueKey") == track),
            scene_key="answer-track",
            purpose="direct",
            certainty="observed",
        ),
        "question": frame_from_fact(
            question_fact,
            scene_key="selected-question",
            purpose="direct",
            certainty="observed",
        ),
        "evidence": frame_from_fact(
            evidence_fact,
            scene_key=(
                f"answer-evidence.{question}"
                if is_unknown_signal(evidence_value)
                else "answer-evidence"
            ),
            purpose=evidence_purpose,
            certainty="unknown" if is_unknown_signal(evidence_value) else "observed",
        ),
        "observable": frame_from_fact(
            observable_fact,
            scene_key="answer-change-condition",
            purpose=observable_purpose,
            certainty="conditional",
        ),
        "uncertainty": frame_from_fact(
            uncertainty_fact,
            scene_key="answer-boundary",
            purpose="direct",
            certainty="unknown" if uncertainty == "unknown" else "bounded",
        ),
    }
    plan = paragraph_plan(
        section_id=facts.section_id,
        paragraph_kind="question-specific-answer",
        conclusion_key=f"{question}-{stage}-{contact}-{track}",
        steps=(
            ("headline", frames["track"]),
            ("opening", frames["question"]),
            ("evidence", frames["evidence"]),
            ("condition", frames["observable"]),
            ("boundary", frames["uncertainty"]),
        ),
        supports=(
            support_from_fact(stage_fact),
            support_from_fact(contact_fact),
            support_from_fact(dynamic_fact),
            support_from_fact(partner_fact),
        ),
    )
    validate_core_answer_rendered(
        rendered,
        frames=frames,
        stage=stage,
        contact=contact,
    )
    validate_paragraph_output(plan, rendered)
    return rendered


def split_sentences(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[。！？!?]+", value) if item.strip()]


@lru_cache(maxsize=1)
def core_answer_sentence_traces() -> dict[str, dict[str, str]]:
    traces: dict[str, dict[str, str]] = {}

    def add(text: str, trace: dict[str, str]) -> None:
        normalized = normalize_copy(text)
        existing = traces.get(normalized)
        if existing is not None and existing != trace:
            raise CoreAnswerNativeChineseError(
                f"core-answer sentence has ambiguous trace: {text}"
            )
        traces[normalized] = trace

    for track, headline in ANSWER_TRACK_HEADLINES.items():
        add(
            headline,
            {
                "kind": "composition",
                "role": "answer-track",
                "valueKey": track,
                "purpose": "headline",
            },
        )
    for question, values in MEANING_OPTIONS.items():
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
    for (stage, question, contact), text in CORE_DIRECT_ANSWER_CATALOG.items():
        add(
            text,
            {
                "kind": "paragraph-composition",
                "role": "question",
                "valueKey": question,
                "purpose": "direct",
                "contributorRole": "contact-status",
                "contributorValueKey": contact,
                "stageRole": "relationship-stage",
                "stageValueKey": stage,
            },
        )
    for dynamic in (*RELATIONSHIP_DYNAMIC_KEYS, "unknown"):
        for text in core_page_dynamic_variants(dynamic):
            add(
                text,
                {
                    "kind": "fact-realization",
                    "role": "central-dynamic",
                    "valueKey": dynamic,
                    "purpose": "situational",
                },
            )
        add(
            CORE_PARAGRAPH_DYNAMIC_THESES[dynamic],
            {
                "kind": "paragraph-realization",
                "role": "central-dynamic",
                "valueKey": dynamic,
                "purpose": "situational",
            },
        )
    for value_key in supported_evidence_signal_values():
        forms = core_signal_forms(value_key)
        for purpose in ("direct", "situational", "relational"):
            add(
                forms.for_purpose(purpose),
                {
                    "kind": "fact-realization",
                    "role": "evidence-signal",
                    "valueKey": value_key,
                    "purpose": purpose,
                },
            )
    for question, text in CORE_UNKNOWN_EVIDENCE_BY_QUESTION.items():
        add(
            text,
            {
                "kind": "fact-realization",
                "role": "evidence-signal",
                "purpose": "direct",
                "certainty": "unknown",
                "sceneKey": f"answer-evidence.{question}",
            },
        )
    for sign, forms in PARTNER_MOON_NEED_FORMS.items():
        for purpose in ("direct", "situational", "relational"):
            add(
                forms.for_purpose(purpose),
                {
                    "kind": "fact-realization",
                    "role": "partner-relationship-need",
                    "valueKey": f"moon.{sign}",
                    "purpose": purpose,
                },
            )
    for value_key, forms in OBSERVABLE_FORMS.items():
        for purpose in ("direct", "situational", "relational"):
            add(
                forms.for_purpose(purpose),
                {
                    "kind": "fact-realization",
                    "role": "observable-sign",
                    "valueKey": value_key,
                    "purpose": purpose,
                },
            )
    for level, values in UNCERTAINTY_COPY.items():
        for text in values:
            add(
                text,
                {
                    "kind": "fact-realization",
                    "role": "uncertainty-level",
                    "valueKey": level,
                    "purpose": "direct",
                },
            )
    return traces


def core_answer_sentence_trace(sentence: str) -> dict[str, str] | None:
    return core_answer_sentence_traces().get(normalize_copy(sentence))


def validate_core_answer_rendered(
    rendered: Mapping[str, str],
    *,
    frames: Mapping[str, ReaderMeaningFrame],
    stage: str,
    contact: str,
) -> None:
    for frame in frames.values():
        frame.validate()
        if frame.section_id != "core-answer":
            raise CoreAnswerNativeChineseError(
                f"core-answer received frame for {frame.section_id}"
            )
    for field, text in rendered.items():
        issues = audit_native_zh_tw_text(text)
        if issues:
            details = ", ".join(f"{item.severity}:{item.id}" for item in issues)
            raise CoreAnswerNativeChineseError(
                f"core-answer:{field}: native Chinese gate failed: {details}"
            )
        regressions = [
            phrase for phrase in CORE_ANSWER_FORBIDDEN_REGRESSIONS if phrase in text
        ]
        if regressions:
            raise CoreAnswerNativeChineseError(
                f"core-answer:{field}: reader regression returned: {regressions}"
            )

    meaning_sentences = split_sentences(rendered["meaning"])
    if len(meaning_sentences) != 1:
        raise CoreAnswerNativeChineseError(
            "core-answer direct answer must be one complete sentence"
        )
    meaning_trace = core_answer_sentence_trace(meaning_sentences[0])
    expected_meaning_trace = {
        "kind": "paragraph-composition",
        "role": "question",
        "valueKey": frames["question"].value_key,
        "purpose": "direct",
        "contributorRole": "contact-status",
        "contributorValueKey": contact,
        "stageRole": "relationship-stage",
        "stageValueKey": stage,
    }
    if meaning_trace != expected_meaning_trace:
        raise CoreAnswerNativeChineseError(
            f"core-answer direct answer lost context ownership: {meaning_trace}"
        )

    body_sentences = split_sentences(rendered["body"])
    body_frames = (frames["evidence"],)
    if len(body_sentences) != len(body_frames):
        raise CoreAnswerNativeChineseError(
            "core-answer body must contain one question-specific evidence sentence"
        )
    owned_sentences = [
        (rendered["headline"], frames["track"], "headline"),
        *[
            (sentence, frame, frame.purpose)
            for sentence, frame in zip(body_sentences, body_frames, strict=True)
        ],
        (rendered["nextMove"], frames["observable"], frames["observable"].purpose),
        (rendered["caution"], frames["uncertainty"], "direct"),
    ]
    for text, frame, purpose in owned_sentences:
        sentences = split_sentences(text)
        if len(sentences) != 1:
            raise CoreAnswerNativeChineseError(
                f"core-answer sentence ownership is ambiguous: {text}"
            )
        trace = core_answer_sentence_trace(sentences[0])
        if trace is None:
            raise CoreAnswerNativeChineseError(
                f"untraceable core-answer sentence: {sentences[0]}"
            )
        if trace.get("role") != frame.role or trace.get("purpose") != purpose:
            raise CoreAnswerNativeChineseError(
                f"core-answer sentence trace does not match frame: {trace}"
            )
        trace_value = str(trace.get("valueKey") or "")
        if trace_value and trace_value != frame.value_key:
            raise CoreAnswerNativeChineseError(
                f"core-answer sentence trace has stale value: {trace_value}"
            )
        trace_scene = str(trace.get("sceneKey") or "")
        if trace_scene and trace_scene != frame.scene_key:
            raise CoreAnswerNativeChineseError(
                f"core-answer sentence trace has stale scene: {trace_scene}"
            )


def core_answer_catalog_errors() -> list[str]:
    try:
        core_answer_sentence_traces()
    except (CoreAnswerNativeChineseError, ValueError) as exc:
        return [str(exc)]
    errors: list[str] = []
    copy_values = [
        *ANSWER_TRACK_HEADLINES.values(),
        *(text for values in MEANING_OPTIONS.values() for text in values),
        *CORE_DIRECT_ANSWER_CATALOG.values(),
        *(
            text
            for dynamic in (*RELATIONSHIP_DYNAMIC_KEYS, "unknown")
            for text in core_page_dynamic_variants(dynamic)
        ),
        *CORE_PARAGRAPH_DYNAMIC_THESES.values(),
        *(
            core_signal_forms(value_key).for_purpose(purpose)
            for value_key in supported_evidence_signal_values()
            for purpose in ("direct", "situational", "relational")
        ),
        *CORE_UNKNOWN_EVIDENCE_BY_QUESTION.values(),
        *(
            forms.for_purpose(purpose)
            for forms in PARTNER_MOON_NEED_FORMS.values()
            for purpose in ("direct", "situational", "relational")
        ),
        *(
            forms.for_purpose(purpose)
            for forms in OBSERVABLE_FORMS.values()
            for purpose in ("direct", "situational", "relational")
        ),
        *(text for values in UNCERTAINTY_COPY.values() for text in values),
    ]
    for text in copy_values:
        issues = audit_native_zh_tw_text(text)
        if issues:
            errors.append(
                f"{text}: " + ", ".join(f"{item.severity}:{item.id}" for item in issues)
            )
    for value_key in supported_evidence_signal_values():
        signal = resolve_relationship_signal(value_key)
        if signal.aspect not in {"sextile", "trine"}:
            continue
        forms = core_signal_forms(value_key)
        for purpose in ("direct", "situational", "relational"):
            text = forms.for_purpose(purpose)
            contradictions = [
                phrase for phrase in CORE_SOFT_SIGNAL_FORBIDDEN if phrase in text
            ]
            if contradictions:
                errors.append(
                    f"{value_key}:{purpose}: soft signal contains hard reaction "
                    f"{contradictions}"
                )
    return errors


__all__ = [
    "ANSWER_TRACK_HEADLINES",
    "CORE_ANSWER_FORBIDDEN_REGRESSIONS",
    "CORE_ANSWER_NATIVE_ZH_TW_CATALOG_VERSION",
    "CORE_DIRECT_ANSWER_CATALOG",
    "CORE_PARAGRAPH_DYNAMIC_THESES",
    "CORE_QUESTION_FOCUS_TERMS",
    "CoreAnswerNativeChineseError",
    "UNCERTAINTY_COPY",
    "core_answer_catalog_errors",
    "core_answer_sentence_trace",
    "core_dynamic_variants",
    "core_page_dynamic_variants",
    "render_core_answer",
    "validate_core_answer_rendered",
]
