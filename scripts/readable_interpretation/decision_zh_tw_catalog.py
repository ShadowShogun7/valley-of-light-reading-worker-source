"""Page-owned decisions composed from existing facts, never upstream prose.

The dynamic is a hidden contributor to a question's change condition or an
action's purpose. It does not receive another standalone relationship thesis.
Boundary and shared-space modes deliberately override chart personalization.
"""

from __future__ import annotations

from .final_narrative_semantic_domains import QUESTION_KEYS, RELATIONSHIP_DYNAMIC_KEYS


DECISION_ZH_TW_CATALOG_VERSION = "decision-zh-tw-v1"

# Complete conditions, rather than adjectives substituted into generic advice.
CORE_CHANGE_CONDITIONS = {
    "communication-repair": "你說明一件事後，他願意確認你的意思，而不是各自重複自己的說法",
    "outer-intensity": "他說過的話和後來做的事能對得上，不再讓你靠猜測填補空白",
    "identity-rhythm": "有不同想法時，你們仍能各自表達，不需要其中一人先放棄自己的選擇",
    "emotional-safety": "你說出不舒服的地方時，他願意聽完，而你也不用反覆證明自己為什麼難過",
    "saturn-pressure": "談到一項具體約定時，你們能說清楚誰做什麼，之後也真的做到",
    "action-conflict": "意見不同時，你們能暫停爭論，之後再回來處理原本那件事",
    "attraction-pursuit": "見面或聊天的熱度過後，他仍願意安排下一次相處，而不只是當下熱情",
    "jupiter-support": "他願意把鼓勵變成一次實際幫忙，而不是只說以後一定會更好",
    "slow-safety": "約好的小事能持續做到，不必靠你一次次提醒才有下文",
    "unknown": "你們能指出一件已經改變的事，而不是只說還有感覺",
}

# One small, concrete action per evidenced repair target. These are instructions,
# not assertions that a specific argument or promise actually occurred.
CONVERSATION_ACTIONS = {
    "communication-repair": (
        "這次把重點放在聽懂彼此，不急著說服對方",
        "沿用正在聊的話題，問一句「你的意思是這樣嗎」，確認一次就停",
        "確認完他的意思，不再補一長段自己的解釋，這一步就完成了",
    ),
    "outer-intensity": (
        "這次只確認一件實際發生的事，不替沒說出口的話猜意思",
        "如果有一件事你不確定，只問那件事是否發生，不追問他是不是不在乎",
        "問過一次就留下答案或暫時沒有答案的事實，不再試探，這一步就完成了",
    ),
    "identity-rhythm": (
        "這次先保留彼此不同的選擇，不把不同意當成不重視",
        "有日常安排要討論時，只說明你的偏好，不要求他一定配合",
        "說清楚一項偏好，不要求他照你的方式決定，這一步就完成了",
    ),
    "emotional-safety": (
        "這次先讓自己的感受被聽見，不要求他馬上安慰或解決",
        "若他願意聽，只說一件讓你難過的小事，說完先停，不列出所有委屈",
        "表達完一件感受，不追問他懂不懂或在不在乎，這一步就完成了",
    ),
    "saturn-pressure": (
        "這次只處理眼前做得到的一項安排，不談整段未來",
        "若有需要確認的日常安排，只問一個明確時間，不連帶要求感情承諾",
        "確認完一項安排或知道他暫時不能答應，就不再催促，這一步就完成了",
    ),
    "action-conflict": (
        "這次先讓談話有停點，不在語氣變重後繼續爭下去",
        "若對話開始變成互相反駁，就說你想先停一下，不再回最後一句",
        "你停下反駁，也沒有再補一則責怪的訊息，這一步就完成了",
    ),
    "attraction-pursuit": (
        "這次不靠增加熱情換取確定感，留意彼此是否都願意花時間",
        "若聊天自然，可以提出一次簡單的見面邀請；他沒答應就不追加邀約",
        "邀請只提一次，不把接受或婉拒解讀成整段關係的結論，這一步就完成了",
    ),
    "jupiter-support": (
        "這次把善意放在一件能做到的事上，不先答應太多",
        "若他提到一件需要幫忙的事，只說明你能幫哪一小部分，不替他全部承擔",
        "說清楚自己能做的部分，沒有加上更多承諾，這一步就完成了",
    ),
    "slow-safety": (
        "這次先維持原本答應的小事，不突然提高相處的要求",
        "完成一件你原本就答應的日常小事，不用它交換見面或更多回覆",
        "把原本答應的事做好，沒有附加感情要求，這一步就完成了",
    ),
    "unknown": (
        "目前還看不清主要問題，先不要為了得到答案做更多事",
        "先寫下一件你已經知道的事和一件還不確定的事，不要把猜測傳給他",
        "分清楚事實和猜測，沒有因此追加訊息，這一步就完成了",
    ),
}

PRIVATE_ACTIONS = {
    "communication-repair": "先寫下你最近一次沒說清楚的重點，用一句話重寫，今天先不要寄出",
    "outer-intensity": "把你確定發生的事和自己的猜測分開寫，先不要再查他的動態",
    "identity-rhythm": "寫下一件你願意協調的事，以及一件不想再勉強自己的事，先不要傳給他",
    "emotional-safety": "先寫下最難過的一件事和你需要的照顧，今天不要把它變成向他的追問",
    "saturn-pressure": "列出一項曾談過的約定，再記下哪些已做到，先不要要求他補新的承諾",
    "action-conflict": "先把想反駁的話留在草稿裡，今天不要追加訊息，也不回去爭最後一句",
    "attraction-pursuit": "記下最近一次熱絡之後是否還有實際安排，先不要再用邀約測試好感",
    "jupiter-support": "寫下一件你實際得到的支持，不把對未來的期待也算進去，今天先不開口",
    "slow-safety": "記下最近幾次說好的小事是否有做到，今天先不要再提醒或追問",
    "unknown": "先寫下你確定知道的情況，不能確認的部分留白，不要急著傳訊息求證",
}


TONE_REPAIR_PURPOSES = {
    "communication-repair": "剛才的話如果讓他覺得被質問，這次先確認意思，不急著反駁",
    "outer-intensity": "如果你把猜測說成了指責，這次先分清楚哪些事真的發生過",
    "identity-rhythm": "如果不同想法變成了互相否定，這次先說清楚你自己的偏好",
    "emotional-safety": "如果你的委屈被聽成責怪，這次只把難過的地方說清楚",
    "saturn-pressure": "如果談安排時像在追究責任，這次先回到一項眼前做得到的事",
    "action-conflict": "如果你們已經開始互相頂嘴，這次先停下反駁，不繼續搶最後一句",
    "attraction-pursuit": "如果想見面的心情變成了催促，這次把邀請留給他自己決定",
    "jupiter-support": "如果好意聽起來像在替他決定，這次先說明你能幫忙的範圍",
    "slow-safety": "如果日常提醒變成了催促，這次先把自己答應的事做好",
    "unknown": "如果你還不清楚哪句話讓彼此不舒服，這次先整理事實，不急著補解釋",
}


def action_decision(mode: str, repair: str, question: str = "any-chance") -> tuple[str, str, str] | None:
    """Return purpose, command, completion; None means a hard policy owns them."""
    if repair not in {*RELATIONSHIP_DYNAMIC_KEYS, "unknown"}:
        raise ValueError(f"unsupported repair target: {repair}")
    if mode not in {"boundary-only", "shared-space-boundary", "observe-or-single-low-stimulation-test", "small-bid-response-led", "tone-repair-in-existing-channel"}:
        raise ValueError(f"unsupported action mode: {mode}")
    if question not in QUESTION_KEYS:
        raise ValueError(f"unsupported action question: {question}")
    if mode in {"boundary-only", "shared-space-boundary"}:
        return None
    if question == "stay-or-let-go":
        return (
            "這次先檢查繼續投入的理由，不用再靠聯絡測試他",
            PRIVATE_ACTIONS[repair],
            "把已發生的事記清楚，沒有為了捨不得而追加聯絡，這一步就完成了",
        )
    if question == "what-did-i-do-wrong":
        return (
            "這次先分清楚你能調整的事，不急著把所有責任攬下來",
            PRIVATE_ACTIONS[repair],
            "記下一件自己能調整的事，不因此反覆道歉或求回應，這一步就完成了",
        )
    if mode == "observe-or-single-low-stimulation-test":
        return (
            "先整理自己已經知道的事，不急著重新開口",
            PRIVATE_ACTIONS[repair],
            "把這件事整理好，今天沒有追加聯絡，這一步就完成了",
        )
    if mode == "tone-repair-in-existing-channel":
        _, command, completion = CONVERSATION_ACTIONS[repair]
        return TONE_REPAIR_PURPOSES[repair], command, completion
    if mode == "small-bid-response-led":
        return CONVERSATION_ACTIONS[repair]
    raise ValueError(f"unsupported action mode: {mode}")


def decision_catalog_errors() -> list[str]:
    domain = {*RELATIONSHIP_DYNAMIC_KEYS, "unknown"}
    errors = []
    for name, catalog in (("core", CORE_CHANGE_CONDITIONS), ("action", CONVERSATION_ACTIONS), ("private", PRIVATE_ACTIONS), ("tone", TONE_REPAIR_PURPOSES)):
        if set(catalog) != domain:
            errors.append(f"{name}: decision coverage differs from registered dynamics")
    return errors
