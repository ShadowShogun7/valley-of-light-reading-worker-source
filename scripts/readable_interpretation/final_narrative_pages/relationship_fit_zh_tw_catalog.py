"""Approved native Traditional Chinese catalog for relationship fit."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal, Mapping

from ..final_narrative_chinese_contract import audit_native_zh_tw_text
from ..final_narrative_chinese_plan import ReaderMeaningFrame
from ..final_narrative_composition import normalize_copy
from ..final_narrative_realization import REALIZATION_PURPOSES, RealizationForms
from ..final_narrative_semantic_domains import (
    RELATIONSHIP_ARCHETYPE_KEYS,
    RELATIONSHIP_DYNAMIC_KEYS,
    RelationshipSignal,
    is_unknown_signal,
)
from ..final_narrative_signal_service import (
    CANONICAL_ASPECT_POLARITY as CANONICAL_POLARITY,
    OUTER_PLANETS,
    PAIR_DOMAINS,
    SIGNAL_KIND_BY_ROLE,
    pair_orientations,
    resolve_relationship_signal,
    supported_relationship_signal_values as supported_signal_values,
)


RELATIONSHIP_FIT_NATIVE_ZH_TW_CATALOG_VERSION = (
    "relationship-fit-native-zh-tw-catalog-v5"
)
ROLE_TO_KIND = {
    role: kind
    for role, kind in SIGNAL_KIND_BY_ROLE.items()
    if role != "evidence-signal"
}
ApprovalStatus = Literal["approved"]


class RelationshipFitNativeChineseError(ValueError):
    """Raised when relationship-fit copy is unsupported or unapproved."""


@dataclass(frozen=True)
class ApprovedRealizationForms:
    forms: RealizationForms
    status: ApprovalStatus = "approved"


def approved(direct: str, situational: str, relational: str) -> ApprovedRealizationForms:
    return ApprovedRealizationForms(RealizationForms(direct, situational, relational))


ARCHETYPE_HEADLINES = {
    "unknown": "目前還看不出固定的關係類型",
    "past-life-intensity": "深刻牽引型",
    "growth-support": "互相支持型",
    "communication-repair": "溝通修復型",
    "mutual-activation": "彼此牽動型",
    "emotional-familiarity": "情緒熟悉型",
    "growth-through-friction": "磨合成長型",
    "fast-spark-conflict": "歡喜冤家型",
    "high-attraction-high-friction": "高吸引高摩擦型",
    "natural-attraction": "自然吸引型",
    "slow-safety": "慢熱安全感型",
}


PRIMARY_DYNAMIC_FORMS = {
    "unknown": approved(
        "目前線索不足，還看不出哪一種相處模式最明顯",
        "相處出現問題時，目前還不能確定哪一個模式最常重複",
        "你們的主要磨合點仍需要從更多真實互動確認",
    ),
    "communication-repair": approved(
        "你們最需要磨合的是溝通，有誤會時能不能重新說清楚",
        "重要話題一變急，你們就容易各自解釋，卻沒有真的聽懂對方",
        "你們能不能走穩，很大部分取決於誤會後是否還願意把話說開",
    ),
    "outer-intensity": approved(
        "你們容易有很強的感受，但感覺和實際選擇之間可能有落差",
        "拉開距離後，你們仍可能反覆想起對方，甚至用猜測補上空白",
        "你們越被強烈感受吸引，越需要看後續有沒有清楚而持續的行動",
    ),
    "identity-rhythm": approved(
        "你們都很在意是否被尊重，受傷時容易先保護自尊",
        "意見不同時，沉默或批評很容易被聽成不被重視",
        "一方覺得被否定時，另一方也容易用更強的立場保護自己",
    ),
    "emotional-safety": approved(
        "你們對彼此的冷熱很敏感，回應不明確時容易開始猜測",
        "一方稍微冷下來，另一方的不安也容易跟著升高",
        "你們的安全感會互相影響，穩定回應比一時安撫更重要",
    ),
    "saturn-pressure": approved(
        "相處一談到責任或長期安排，彼此就容易變得保守",
        "輕鬆相處時不一定有問題，一談未來就容易有人慢下來",
        "一方越想確認承諾，另一方越容易先衡量自己能不能承擔",
    ),
    "action-conflict": approved(
        "你們都想用自己的速度處理問題，著急時很容易互相頂住",
        "兩邊都急著處理時，小事也可能很快變成正面衝突",
        "一方越想立刻解決，另一方的反應也越容易變硬",
    ),
    "attraction-pursuit": approved(
        "你們不缺靠近的火花，真正的磨合在熱度過後能否持續投入",
        "靠近可以很快，後續是否仍有雙方行動才看得出能不能走穩",
        "一方越用熱度確認關係，越需要看另一方之後會不會繼續靠近",
    ),
    "jupiter-support": approved(
        "你們容易鼓勵彼此，關鍵是好意能不能變成實際支持",
        "一起談未來時很有希望，回到日常仍要看答應的事有沒有做到",
        "你們能看見彼此的可能性，但支持要靠雙方真正投入才會留下",
    ),
    "slow-safety": approved(
        "你們需要穩定而可預期的互動，信任才會慢慢建立",
        "關係突然加速時，其中一方容易退回原本的安全距離",
        "你們越能維持小而穩定的互動，越容易放心地靠近",
    ),
}


FIT_PARAGRAPH_THESES = {
    "unknown": "目前最常重複的相處模式還不夠清楚，需要從更多真實互動確認",
    "communication-repair": "你們平常不一定沒話說，真正的差別在誤會出現後能不能重新聽懂對方",
    "outer-intensity": "你們的牽引很強，但感受越強，越需要分清想像和實際選擇",
    "identity-rhythm": "你們都很在意自己是否被尊重，受傷時也容易先保護自尊",
    "emotional-safety": "你們很容易察覺對方的冷熱，回應一不明確，不安也會跟著升高",
    "saturn-pressure": "你們的主要磨合在責任和未來，一談到長期安排，兩個人的速度就容易慢下來",
    "action-conflict": "你們的主要磨合在處理問題的速度，兩個人一急著解決，就很容易從討論變成爭執",
    "attraction-pursuit": "你們不缺靠近的火花，真正的差別在熱度過後還有沒有雙方行動",
    "jupiter-support": "你們容易看見彼此的可能性，真正的考驗是鼓勵能不能落到日常支持",
    "slow-safety": "你們需要在穩定相處裡慢慢累積信任，突然加速反而容易讓其中一方退開",
}


FIT_PARAGRAPH_SECONDARIES = {
    "unknown": "另外，其他相處線索目前還不夠清楚，需要再用真實互動確認",
    "communication-repair": "另外，誤會出現後，你們也容易急著解釋，反而漏掉真正重點",
    "outer-intensity": "另外，距離拉開後，強烈感受也可能讓你們用猜測補上空白",
    "identity-rhythm": "另外，意見不同時，你們都容易先保護自尊，很難承認自己受傷",
    "emotional-safety": "另外，一方稍微冷下來，另一方的不安也容易跟著升高",
    "saturn-pressure": "另外，話題一碰到責任和未來，回應就容易變慢也更保留",
    "action-conflict": "另外，兩個人同時著急時，原本想處理問題也容易變成互相頂住",
    "attraction-pursuit": "另外，靠近可以很快，熱度過後才看得出誰願意繼續投入",
    "jupiter-support": "另外，你們很會給彼此希望，但答應的事有沒有做到更重要",
    "slow-safety": "另外，關係突然加速時，其中一方容易退回原本的安全距離",
}


FIT_PARAGRAPH_UNKNOWN_SIGNALS = {
    "attraction-signal": "目前還看不出你們最自然的靠近方式",
    "friction-signal": "但目前還看不出你們最容易在哪種情況下卡住",
    "growth-signal": "目前還看不出哪一種調整最適合你們長期相處",
}


SECONDARY_DYNAMIC_FORMS = {
    "unknown": approved(
        "其他相處線索目前還不夠明確",
        "目前還沒有第二個明確模式需要放大",
        "其他可能的磨合點仍需要更多相處才能確認",
    ),
    "communication-repair": approved(
        "你們平常不一定沒話說，真正容易卡住的是誤會後怎麼接回來",
        "對話開始互相搶著解釋時，真正想說的內容反而容易被漏掉",
        "你越急著補充，他越可能只聽見壓力，最後兩邊都錯過重點",
    ),
    "outer-intensity": approved(
        "強烈感受很容易留下，但不能代替後續的現實選擇",
        "互動停下來後，強烈感受仍可能讓你們反覆猜對方在想什麼",
        "你們越在意這份牽引，越需要分清感受和真正發生的行動",
    ),
    "identity-rhythm": approved(
        "彼此是否感到被尊重，會直接影響你們願不願意繼續對話",
        "討論變成誰對誰錯時，你們會先守住自尊，很難承認自己受傷",
        "一方先保護自尊時，另一方也容易把距離理解成否定",
    ),
    "emotional-safety": approved(
        "你們很容易察覺對方的冷熱，小反應也可能變成不安",
        "回應忽冷忽熱時，你們都容易把小變化想成關係出了問題",
        "一個人的退開會放大另一個人的猜測，讓安全感更難恢復",
    ),
    "saturn-pressure": approved(
        "責任和承諾會讓你們的回應比平常更慢、更保留",
        "話題碰到承諾或長期安排時，回應會明顯變慢，也更保留",
        "一方越想確認未來，另一方越容易先看見壓力和限制",
    ),
    "action-conflict": approved(
        "兩邊同時用力時，原本想處理的問題很容易變成互相對抗",
        "處理問題的速度一不同，你們就容易從合作變成互相阻擋",
        "你越想加快處理，他越容易用更強的反應守住自己的速度",
    ),
    "attraction-pursuit": approved(
        "一時靠近可以很快，真正的差別在熱度之後還有沒有行動",
        "互動熱起來時靠近很自然，熱度下降後才看得出誰會繼續投入",
        "你們越被火花帶動，越需要看主動和照顧能不能留在日常",
    ),
    "jupiter-support": approved(
        "彼此很容易給出希望，但支持需要真正完成才會累積信任",
        "一起規劃時容易互相鼓勵，真正執行時才看得出支持是否可靠",
        "你們能互相鼓勵，但好意只有落到行動才會真正支撐關係",
    ),
    "slow-safety": approved(
        "這段關係更適合慢慢累積，突然加速反而容易退回原位",
        "互動突然變密集或話題變重時，其中一方很容易先退開",
        "你們需要用可預期的小互動確認安全，不能只靠一次熱絡",
    ),
}


ATTRACTION_STEMS = {
    ("sun", "moon"): "{actor}坦白表達自己時，{receiver}很快就會有情緒上的回應",
    ("moon", "sun"): "{actor}流露真實感受時，{receiver}很容易注意到這份情緒",
    ("sun", "venus"): "{actor}展現原本的樣子時，{receiver}很容易看見值得欣賞的地方",
    ("venus", "sun"): "{actor}表達欣賞時，{receiver}會更明顯感到自己被看見",
    ("sun", "mars"): "{actor}表現得很直接時，{receiver}通常也會更主動地回應",
    ("mars", "sun"): "{actor}主動靠近時，{receiver}通常會明確注意到這份心意",
    ("venus", "mars"): "{actor}表達好感時，{receiver}容易想更主動地靠近",
    ("mars", "venus"): "{actor}主動靠近時，{receiver}通常也會用好感回應",
    ("moon", "venus"): "{actor}流露感受時，{receiver}很自然會用關心或好感回應",
    ("venus", "moon"): "{actor}表達在意時，{receiver}很容易感到被照顧",
    ("moon", "moon"): "{actor}情緒有變化時，{receiver}往往很快就能感受到",
    ("venus", "venus"): "{actor}表達喜歡時，{receiver}通常不難感受到其中的好意",
}


FRICTION_STEMS = {
    ("mercury", "mars"): "{actor}急著把話說清楚時，{receiver}容易立刻反駁或採取行動",
    ("mars", "mercury"): "{actor}一急著把話說清楚，{receiver}就會開始解釋或糾正細節",
    ("mercury", "moon"): "{actor}專心說明道理時，{receiver}可能先被語氣影響",
    ("moon", "mercury"): "{actor}情緒一上來，{receiver}就更難把原本想說的話說清楚",
    ("mercury", "sun"): "{actor}指出問題時，{receiver}容易覺得整個人被否定",
    ("sun", "mercury"): "{actor}堅持自己的立場時，{receiver}會更想用理由說服",
    ("mercury", "venus"): "{actor}急著講清楚時，{receiver}可能更在意口氣和感受",
    ("venus", "mercury"): "{actor}先顧及氣氛時，{receiver}可能覺得真正問題沒有說清楚",
    ("mercury", "saturn"): "{actor}想把話說完整時，{receiver}容易先檢查責任、規則或後果",
    ("saturn", "mercury"): "{actor}提出標準或責任時，{receiver}說話會變得更小心",
    ("mercury", "mercury"): "{actor}用自己的方式解釋時，{receiver}可能理解成另一個意思",
    ("mars", "mars"): "{actor}想按自己的速度處理時，{receiver}也容易立刻用行動回應",
    ("mars", "saturn"): "{actor}想加快進度時，{receiver}容易先踩住煞車",
    ("saturn", "mars"): "{actor}要求先確認界線時，{receiver}容易覺得行動被擋住",
    ("moon", "mars"): "{actor}情緒被碰到時，{receiver}容易立刻用行動或脾氣回應",
    ("mars", "moon"): "{actor}反應太直接時，{receiver}的情緒容易先受傷",
    ("moon", "moon"): "{actor}想靠近尋求安慰時，{receiver}可能正需要先退開",
    ("moon", "venus"): "{actor}期待被照顧時，{receiver}不一定知道該怎麼表達",
    ("venus", "moon"): "{actor}用自己的方式示好時，{receiver}不一定感到被照顧",
    ("moon", "saturn"): "{actor}需要安慰時，{receiver}可能先沉默、講道理或拉開距離",
    ("saturn", "moon"): "{actor}先談責任和現實時，{receiver}卻容易覺得感受沒有被接住",
    ("venus", "mars"): "{actor}想用好感拉近距離時，{receiver}可能回得太快或太直接",
    ("mars", "venus"): "{actor}把距離拉近時，{receiver}可能覺得速度太快、壓力太大",
    ("venus", "venus"): "{actor}用自己的方式示好時，{receiver}不一定能把它當成愛的表達",
    ("venus", "saturn"): "{actor}想確認被珍惜時，{receiver}可能先考慮承諾和現實限制",
    ("saturn", "venus"): "{actor}先談責任或界線時，{receiver}會更保守地表達好感",
    ("sun", "saturn"): "{actor}想自然做自己時，{receiver}可能先提出標準或限制",
    ("saturn", "sun"): "{actor}提出責任和要求時，{receiver}容易覺得自己做得不夠好",
    ("sun", "moon"): "{actor}照自己的方式做決定時，{receiver}的情緒需要可能被忽略",
    ("moon", "sun"): "{actor}需要情緒回應時，{receiver}可能先堅持自己的做法",
    ("sun", "venus"): "{actor}照自己的方式表達時，{receiver}不一定感受到其中的好意",
    ("venus", "sun"): "{actor}想讓{receiver}感到被欣賞時，{receiver}仍可能覺得自己沒有被真正理解",
    ("sun", "mars"): "{actor}想主導方向時，{receiver}容易用行動或脾氣回應",
    ("mars", "sun"): "{actor}直接採取行動時，{receiver}容易覺得自己的想法被壓過",
}


GROWTH_STEMS = {
    ("mars", "saturn"): "{actor}願意放慢處理速度，{receiver}就比較能說清楚自己的界線",
    ("saturn", "mars"): "{actor}把界線和時間說具體，{receiver}就比較知道怎麼行動",
    ("moon", "saturn"): "{actor}把需要的安慰說清楚，{receiver}就比較知道怎麼陪伴",
    ("saturn", "moon"): "{actor}先接住感受再談現實，{receiver}就比較不需要反覆確認",
    ("sun", "saturn"): "{actor}把期待拆成眼前做得到的事，{receiver}就比較能承擔",
    ("saturn", "sun"): "{actor}談責任時先肯定{receiver}已經做到的部分，{receiver}就比較不會把要求聽成否定",
    ("venus", "saturn"): "{actor}用穩定的小行動表達在意，{receiver}就比較能逐漸放心",
    ("saturn", "venus"): "{actor}把能做到的承諾說清楚，{receiver}就比較敢自然表達好感",
    ("mercury", "saturn"): "{actor}先約好談話範圍，{receiver}就比較能把重要問題談完",
    ("saturn", "mercury"): "{actor}把要求說得具體而不帶批評，{receiver}就比較願意繼續說",
}


ASPECT_ENDINGS = {
    "attraction": {
        "direct": {
            "conjunction": "，彼此的注意和感受會很快加深",
            "sextile": "，靠近時通常不需要太多試探",
            "trine": "，好感容易在日常相處中自然流動",
            "square": "，吸引和敏感常會一起被放大",
            "opposition": "，彼此會互相注意，也容易出現拉扯",
            "quincunx": "，好感存在，接近方式卻不一定對得上",
        },
        "situational": {
            "conjunction": "，互動一開始就容易感到對方的存在",
            "sextile": "，氣氛放鬆時很容易自然接近",
            "trine": "，平常相處時不太需要刻意營造好感",
            "square": "，越在意對方，越容易碰到敏感點",
            "opposition": "，一個人靠近時，另一個人可能同時想退開",
            "quincunx": "，靠近後才容易發現彼此的節奏不同",
        },
        "relational": {
            "conjunction": "，兩個人很快就會投入這段互動",
            "sextile": "，彼此通常願意為靠近多走一步",
            "trine": "，你們容易在自然相處中累積好感",
            "square": "，你們越想靠近，彼此的敏感也越明顯",
            "opposition": "，你們會互相吸引，也容易在距離上拉扯",
            "quincunx": "，你們有好感，卻可能一直錯過對方的靠近方式",
        },
    },
    "friction": {
        "direct": {
            "conjunction": "，兩種反應會一起出現，原本的小事也容易被放大",
            "sextile": "，差異看得見，但通常仍有空間說開",
            "trine": "，彼此較能自然調整，不一定每次都衝突",
            "square": "，兩邊很容易互相頂住，口氣也跟著變硬",
            "opposition": "，雙方常站到相反位置，越說服越難靠近",
            "quincunx": "，彼此常抓不到真正重點，誤會會慢慢累積",
        },
        "situational": {
            "conjunction": "，壓力一高，原本的小事也容易被放大",
            "sextile": "，願意停下來確認時，通常還能重新聽懂",
            "trine": "，有分歧時仍比較容易找到可調整的做法",
            "square": "，一著急就容易互相頂住，對話很快變硬",
            "opposition": "，一談到分歧就容易各站一邊，誰也聽不進去",
            "quincunx": "，談得越久越容易錯開重點，最後都覺得沒被理解",
        },
        "relational": {
            "conjunction": "，兩個人的壓力會一起升高，原本的問題反而談不清楚",
            "sextile": "，你們看得見差異，也比較有機會一起調整",
            "trine": "，你們通常能在衝突變大前自然換一種做法",
            "square": "，你們越想解決，越容易用力過頭而互相防備",
            "opposition": "，你們容易用相反方式保護自己，距離也跟著拉大",
            "quincunx": "，你們常在不同重點上努力，久了都覺得對方不懂",
        },
    },
    "growth": {
        "direct": {
            "conjunction": "，這個改變會很快影響整體相處",
            "sextile": "，雙方比較容易一起配合",
            "trine": "，新的節奏比較容易留在日常",
            "square": "，但需要刻意練習，才不會回到原本衝突",
            "opposition": "，也要避免只要求其中一方配合",
            "quincunx": "，做法需要幾次調整才能慢慢對上",
        },
        "situational": {
            "conjunction": "，一開始改變就能看見互動明顯不同",
            "sextile": "，從一件小事開始，雙方通常比較做得到",
            "trine": "，持續幾次後，新的相處方式會更自然",
            "square": "，壓力一高仍可能回到舊方法，需要先提醒彼此",
            "opposition": "，兩邊都要調整，才不會變成一個人一直讓步",
            "quincunx": "，每次只修正一點，才比較容易找到合適節奏",
        },
        "relational": {
            "conjunction": "，你們很快就能看出相處是否真的不同",
            "sextile": "，這種做法也比較容易持續",
            "trine": "，新的相處方式比較容易慢慢建立信任",
            "square": "，你們需要一起練習，否則很容易回到原本衝突",
            "opposition": "，你們都要參與，不能只由其中一方退讓",
            "quincunx": "，你們需要反覆調整，才會找到雙方都舒服的做法",
        },
    },
}


FIT_PARAGRAPH_ASPECT_ENDINGS = {
    "attraction": {
        "conjunction": "，互動很快就會升溫",
        "sextile": "，互動通常接得很自然",
        "trine": "，靠近時比較不費力",
        "square": "，吸引來得快，也容易忽近忽遠",
        "opposition": "，吸引很強，靠近後也容易拉扯",
        "quincunx": "，彼此有好感，卻常抓不到同一個節奏",
    },
    "friction": {
        "conjunction": "，壓力很快就會升高",
        "sextile": "，通常還找得到調整空間",
        "trine": "，冷靜後比較容易重新對話",
        "square": "，很容易互相頂住",
        "opposition": "，常用相反方式保護自己",
        "quincunx": "，容易各自用力卻錯過重點",
    },
    "growth": {
        "conjunction": "，改變很快就看得出來",
        "sextile": "，從一件小事開始比較做得到",
        "trine": "，新的做法比較容易留下來",
        "square": "，需要一起練習才不會重演",
        "opposition": "，不能只靠其中一方退讓",
        "quincunx": "，需要幾次調整才會慢慢對上",
    },
}


UNKNOWN_SIGNAL_FORMS = {
    "attraction-signal": approved(
        "目前的合盤線索還不足以說明你們最自然的吸引方式",
        "目前還看不出什麼情況最容易讓你們自然靠近",
        "你們的吸引方式仍需要更多合盤線索才能確認",
    ),
    "friction-signal": approved(
        "目前的合盤線索還不足以指出你們最容易卡住的地方",
        "目前還看不出什麼情況最容易讓你們產生摩擦",
        "你們的主要摩擦方式仍需要更多合盤線索才能確認",
    ),
    "growth-signal": approved(
        "目前從合盤裡還看不出最適合你們的修復方式",
        "目前還看不出什麼做法最能減少你們的摩擦",
        "目前還看不出哪種調整最適合你們",
    ),
}


FIT_BOUNDARY = "合盤只能說明你們容易出現的相處模式，能否走穩仍要看雙方實際怎麼做"


RELATIONSHIP_FIT_FORBIDDEN_REGRESSIONS = (
    "集中時，你的靠近和處理衝突的速度一明顯，他的表達好感的方式也會被帶動",
    "你們之間有會互相反應的地方，但它更像一個位置，不是直接等於關係答案",
    "一明顯，也會被帶動",
    "會牽動你的",
    "會牽動他的",
)


PAIR_STEMS = {
    "attraction": ATTRACTION_STEMS,
    "friction": FRICTION_STEMS,
    "growth": GROWTH_STEMS,
}

PERSONAL_PLANET_ACTIONS = {
    "sun": "表達自己的立場",
    "moon": "流露情緒",
    "mercury": "說出想法",
    "venus": "表達好感",
    "mars": "主動靠近或處理問題",
    "jupiter": "談共同期待",
    "saturn": "提出責任或界線",
}
PERSONAL_PLANET_TARGETS = {
    "sun": "自我肯定",
    "moon": "情緒",
    "mercury": "想法",
    "venus": "好感",
    "mars": "行動節奏",
    "jupiter": "期待",
    "saturn": "責任感",
}
OUTER_PLANET_ACTIONS = {
    "uranus": "忽然改變距離",
    "neptune": "把想像放進關係",
    "pluto": "表現出強烈在意",
    "outer": "帶來強烈或反覆的感受",
}
OUTER_PLANET_REACTIONS = {
    "uranus": "容易突然靠近或退開",
    "neptune": "容易用想像補上空白",
    "pluto": "容易變得更在意也更防備",
    "outer": "容易把原本的感受繼續放大",
}


def finish_sentence(value: str) -> str:
    text = str(value or "").strip()
    return text if text.endswith(("。", "！", "？")) else f"{text}。"


def person_subject(person_key: str) -> str:
    if person_key == "persona":
        return "你"
    if person_key == "personb":
        return "他"
    raise RelationshipFitNativeChineseError(f"unsupported relationship person: {person_key}")


def outer_intensity_stem(signal: RelationshipSignal) -> str:
    actor = person_subject(signal.actor_person)
    receiver = person_subject(signal.receiver_person)
    actor_planet = signal.actor_planet
    receiver_planet = signal.receiver_planet
    if actor_planet not in OUTER_PLANETS and receiver_planet not in OUTER_PLANETS:
        raise RelationshipFitNativeChineseError(
            "outer-planet-intensity signal contains no outer planet"
        )
    if actor_planet in OUTER_PLANETS and receiver_planet not in OUTER_PLANETS:
        return (
            f"{actor}{OUTER_PLANET_ACTIONS[actor_planet]}時，{receiver}的"
            f"{PERSONAL_PLANET_TARGETS[receiver_planet]}容易失去原有節奏"
        )
    if actor_planet not in OUTER_PLANETS and receiver_planet in OUTER_PLANETS:
        return (
            f"{actor}{PERSONAL_PLANET_ACTIONS[actor_planet]}時，{receiver}"
            f"{OUTER_PLANET_REACTIONS[receiver_planet]}"
        )
    return (
        f"{actor}{OUTER_PLANET_ACTIONS[actor_planet]}時，{receiver}"
        f"{OUTER_PLANET_REACTIONS[receiver_planet]}"
    )


def signal_stem(signal: RelationshipSignal) -> str:
    if signal.kind == "friction" and signal.pair_key == "outer-planet-intensity":
        return outer_intensity_stem(signal)
    template = PAIR_STEMS[signal.kind].get(
        (signal.actor_planet, signal.receiver_planet)
    )
    if template is None:
        raise RelationshipFitNativeChineseError(
            f"unsupported {signal.kind} direction for {signal.pair_key}: "
            f"{signal.actor_planet}>{signal.receiver_planet}"
        )
    return template.format(
        actor=person_subject(signal.actor_person),
        receiver=person_subject(signal.receiver_person),
    )


def signal_forms(value_key: str, *, expected_kind: str) -> RealizationForms:
    signal = resolve_relationship_signal(value_key, expected_kind=expected_kind)
    stem = signal_stem(signal)
    endings = ASPECT_ENDINGS[expected_kind]
    return RealizationForms(
        stem + endings["direct"][signal.aspect],
        stem + endings["situational"][signal.aspect],
        stem + endings["relational"][signal.aspect],
    )


def realize_relationship_fit_frame(frame: ReaderMeaningFrame) -> str:
    frame.validate()
    if frame.section_id != "relationship-fit":
        raise RelationshipFitNativeChineseError(
            f"relationship-fit catalog received frame for {frame.section_id}"
        )
    if frame.role == "primary-dynamic":
        entry = PRIMARY_DYNAMIC_FORMS.get(frame.value_key)
        if entry is None:
            raise RelationshipFitNativeChineseError(
                f"missing primary dynamic realization: {frame.value_key}"
            )
        return entry.forms.for_purpose(frame.purpose)
    if frame.role == "secondary-dynamic":
        entry = SECONDARY_DYNAMIC_FORMS.get(frame.value_key)
        if entry is None:
            raise RelationshipFitNativeChineseError(
                f"missing secondary dynamic realization: {frame.value_key}"
            )
        return entry.forms.for_purpose(frame.purpose)
    kind = ROLE_TO_KIND.get(frame.role)
    if kind is None:
        raise RelationshipFitNativeChineseError(
            f"unsupported relationship-fit frame role: {frame.role}"
        )
    if is_unknown_signal(frame.value_key):
        return UNKNOWN_SIGNAL_FORMS[frame.role].forms.for_purpose(frame.purpose)
    return signal_forms(frame.value_key, expected_kind=kind).for_purpose(frame.purpose)


def paragraph_relationship_fit_value(role: str, value_key: str) -> str:
    if role == "primary-dynamic":
        try:
            return FIT_PARAGRAPH_THESES[value_key]
        except KeyError as exc:
            raise RelationshipFitNativeChineseError(
                f"missing relationship paragraph thesis: {value_key}"
            ) from exc
    if role == "secondary-dynamic":
        try:
            return FIT_PARAGRAPH_SECONDARIES[value_key]
        except KeyError as exc:
            raise RelationshipFitNativeChineseError(
                f"missing secondary paragraph realization: {value_key}"
            ) from exc

    kind = ROLE_TO_KIND.get(role)
    if kind is None:
        raise RelationshipFitNativeChineseError(
            f"unsupported relationship paragraph role: {role}"
        )
    if is_unknown_signal(value_key):
        return FIT_PARAGRAPH_UNKNOWN_SIGNALS[role]

    signal = resolve_relationship_signal(value_key, expected_kind=kind)
    text = signal_stem(signal) + FIT_PARAGRAPH_ASPECT_ENDINGS[kind][signal.aspect]
    prefix = {
        "attraction-signal": "",
        "friction-signal": "但",
        "growth-signal": "要讓關係走穩，",
    }[role]
    return f"{prefix}{text}"


def paragraph_relationship_fit_frame(frame: ReaderMeaningFrame) -> str:
    frame.validate()
    if frame.section_id != "relationship-fit":
        raise RelationshipFitNativeChineseError(
            f"relationship paragraph received frame for {frame.section_id}"
        )
    return paragraph_relationship_fit_value(frame.role, frame.value_key)


def headline_for(value_key: str) -> str:
    try:
        return ARCHETYPE_HEADLINES[value_key]
    except KeyError as exc:
        raise RelationshipFitNativeChineseError(
            f"missing archetype headline: {value_key}"
        ) from exc


def caution_for() -> str:
    return FIT_BOUNDARY


def split_sentences(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[。！？!?]+", value) if item.strip()]


@lru_cache(maxsize=1)
def relationship_fit_sentence_traces() -> dict[str, dict[str, str]]:
    traces: dict[str, dict[str, str]] = {}

    def add(text: str, trace: dict[str, str]) -> None:
        normalized = normalize_copy(text)
        if normalized in traces and traces[normalized] != trace:
            raise RelationshipFitNativeChineseError(
                f"relationship-fit sentence has ambiguous trace: {text}"
            )
        traces[normalized] = trace

    for value_key, headline in ARCHETYPE_HEADLINES.items():
        add(
            headline,
            {
                "kind": "composition",
                "role": "relationship-archetype",
                "valueKey": value_key,
                "purpose": "headline",
            },
        )
    for role, catalog in (
        ("primary-dynamic", PRIMARY_DYNAMIC_FORMS),
        ("secondary-dynamic", SECONDARY_DYNAMIC_FORMS),
    ):
        for value_key, entry in catalog.items():
            for purpose in REALIZATION_PURPOSES:
                add(
                    entry.forms.for_purpose(purpose),
                    {
                        "kind": "fact-realization",
                        "role": role,
                        "valueKey": value_key,
                        "purpose": purpose,
                    },
                )
    for value_key, text in FIT_PARAGRAPH_THESES.items():
        add(
            text,
            {
                "kind": "paragraph-realization",
                "role": "primary-dynamic",
                "valueKey": value_key,
                "purpose": "direct",
            },
        )
    for value_key in SECONDARY_DYNAMIC_FORMS:
        add(
            paragraph_relationship_fit_value("secondary-dynamic", value_key),
            {
                "kind": "paragraph-realization",
                "role": "secondary-dynamic",
                "valueKey": value_key,
                "purpose": "situational",
            },
        )
    for role, kind in ROLE_TO_KIND.items():
        for value_key in supported_signal_values(kind):
            forms = signal_forms(value_key, expected_kind=kind)
            for purpose in REALIZATION_PURPOSES:
                add(
                    forms.for_purpose(purpose),
                    {
                        "kind": "fact-realization",
                        "role": role,
                        "valueKey": value_key,
                        "purpose": purpose,
                    },
                )
            paragraph_purpose = (
                "situational" if role == "friction-signal" else "relational"
            )
            add(
                paragraph_relationship_fit_value(role, value_key),
                {
                    "kind": "paragraph-realization",
                    "role": role,
                    "valueKey": value_key,
                    "purpose": paragraph_purpose,
                },
            )
        for purpose in REALIZATION_PURPOSES:
            add(
                UNKNOWN_SIGNAL_FORMS[role].forms.for_purpose(purpose),
                {
                    "kind": "fact-realization",
                    "role": role,
                    "purpose": purpose,
                    "certainty": "unknown",
                },
            )
        unresolved_value = f"{kind}:{kind}dynamics:unresolved"
        paragraph_purpose = (
            "situational" if role == "friction-signal" else "relational"
        )
        add(
            paragraph_relationship_fit_value(role, unresolved_value),
            {
                "kind": "paragraph-realization",
                "role": role,
                "purpose": paragraph_purpose,
                "certainty": "unknown",
            },
        )
    add(
        FIT_BOUNDARY,
        {"kind": "composition", "role": "fit-boundary", "purpose": "boundary"},
    )
    return traces


def relationship_fit_sentence_trace(text: str) -> dict[str, str] | None:
    return relationship_fit_sentence_traces().get(normalize_copy(text))


def _assert_trace(
    text: str,
    *,
    kind: str,
    role: str,
    purpose: str,
    value_key: str = "",
    certainty: str = "",
) -> None:
    expected = {"kind": kind, "role": role, "purpose": purpose}
    if value_key:
        expected["valueKey"] = value_key
    if certainty:
        expected["certainty"] = certainty
    actual = relationship_fit_sentence_trace(text)
    if actual != expected:
        raise RelationshipFitNativeChineseError(
            f"untraceable relationship-fit sentence: expected={expected} "
            f"actual={actual} text={text}"
        )


def validate_relationship_fit_rendered(
    rendered: Mapping[str, str],
    *,
    archetype_frame: ReaderMeaningFrame,
    primary_frame: ReaderMeaningFrame,
    secondary_frame: ReaderMeaningFrame | None,
    attraction_frame: ReaderMeaningFrame,
    friction_frame: ReaderMeaningFrame,
    growth_frame: ReaderMeaningFrame,
) -> None:
    frames = [
        archetype_frame,
        primary_frame,
        attraction_frame,
        friction_frame,
        growth_frame,
    ]
    if secondary_frame is not None:
        frames.append(secondary_frame)
    for frame in frames:
        frame.validate()
        if frame.section_id != "relationship-fit":
            raise RelationshipFitNativeChineseError(
                f"relationship-fit renderer received frame for {frame.section_id}"
            )
    expected_purposes = {
        "relationship-archetype": "direct",
        "primary-dynamic": "direct",
        "secondary-dynamic": "situational",
        "attraction-signal": "relational",
        "friction-signal": "situational",
        "growth-signal": "relational",
    }
    for frame in frames:
        if frame.purpose != expected_purposes[frame.role]:
            raise RelationshipFitNativeChineseError(
                f"wrong relationship-fit purpose: {frame.role}:{frame.purpose}"
            )

    attraction_text = paragraph_relationship_fit_frame(attraction_frame)
    friction_text = paragraph_relationship_fit_frame(friction_frame)
    secondary_text = (
        paragraph_relationship_fit_frame(secondary_frame)
        if secondary_frame is not None
        else ""
    )
    expected = {
        "headline": headline_for(archetype_frame.value_key),
        "meaning": finish_sentence(paragraph_relationship_fit_frame(primary_frame)),
        "body": "".join(
            finish_sentence(value)
            for value in (attraction_text, friction_text, secondary_text)
            if value
        ),
        "nextMove": finish_sentence(paragraph_relationship_fit_frame(growth_frame)),
        "caution": finish_sentence(caution_for()),
    }
    if dict(rendered) != expected:
        raise RelationshipFitNativeChineseError(
            "relationship-fit output does not match its owned meaning frames"
        )

    for field, text in expected.items():
        issues = audit_native_zh_tw_text(text)
        if issues:
            details = ", ".join(f"{item.severity}:{item.id}" for item in issues)
            raise RelationshipFitNativeChineseError(
                f"relationship-fit:{field}: native Chinese gate failed: {details}"
            )
        regressions = [
            phrase for phrase in RELATIONSHIP_FIT_FORBIDDEN_REGRESSIONS if phrase in text
        ]
        if regressions:
            raise RelationshipFitNativeChineseError(
                f"relationship-fit:{field}: reader regression returned: {regressions}"
            )

    _assert_trace(
        expected["headline"],
        kind="composition",
        role="relationship-archetype",
        value_key=archetype_frame.value_key,
        purpose="headline",
    )
    _assert_trace(
        paragraph_relationship_fit_frame(primary_frame),
        kind="paragraph-realization",
        role=primary_frame.role,
        value_key=primary_frame.value_key,
        purpose=primary_frame.purpose,
    )
    body_frames = [attraction_frame, friction_frame]
    if secondary_frame is not None:
        body_frames.append(secondary_frame)
    body_sentences = split_sentences(expected["body"])
    if len(body_sentences) != len(body_frames):
        raise RelationshipFitNativeChineseError(
            "relationship-fit body sentence ownership is incomplete"
        )
    for sentence, frame in zip(body_sentences, body_frames, strict=True):
        unknown = frame.role in ROLE_TO_KIND and is_unknown_signal(frame.value_key)
        _assert_trace(
            sentence,
            kind="paragraph-realization",
            role=frame.role,
            value_key="" if unknown else frame.value_key,
            purpose=frame.purpose,
            certainty="unknown" if unknown else "",
        )
    growth_unknown = is_unknown_signal(growth_frame.value_key)
    _assert_trace(
        paragraph_relationship_fit_frame(growth_frame),
        kind="paragraph-realization",
        role=growth_frame.role,
        value_key="" if growth_unknown else growth_frame.value_key,
        purpose=growth_frame.purpose,
        certainty="unknown" if growth_unknown else "",
    )
    _assert_trace(
        caution_for(),
        kind="composition",
        role="fit-boundary",
        purpose="boundary",
    )


def catalog_errors() -> list[str]:
    errors: list[str] = []
    expected_archetypes = {*RELATIONSHIP_ARCHETYPE_KEYS, "unknown"}
    expected_dynamics = {*RELATIONSHIP_DYNAMIC_KEYS, "unknown"}
    if set(ARCHETYPE_HEADLINES) != expected_archetypes:
        errors.append("relationship archetype headline domain is incomplete")
    for identity, catalog in (
        ("primary-dynamic", PRIMARY_DYNAMIC_FORMS),
        ("secondary-dynamic", SECONDARY_DYNAMIC_FORMS),
    ):
        if set(catalog) != expected_dynamics:
            errors.append(f"{identity} native catalog domain is incomplete")
        for value_key, entry in catalog.items():
            if entry.status != "approved":
                errors.append(f"{identity}:{value_key}: realization is not approved")
            try:
                entry.forms.validate(f"{identity}:{value_key}")
            except ValueError as exc:
                errors.append(str(exc))
    if set(FIT_PARAGRAPH_THESES) != expected_dynamics:
        errors.append("relationship paragraph thesis domain is incomplete")
    if set(FIT_PARAGRAPH_SECONDARIES) != expected_dynamics:
        errors.append("relationship paragraph secondary domain is incomplete")
    if set(FIT_PARAGRAPH_UNKNOWN_SIGNALS) != set(ROLE_TO_KIND):
        errors.append("relationship paragraph unknown-signal domain is incomplete")

    expected_stems: dict[str, set[tuple[str, str]]] = {}
    for kind, pairs in PAIR_DOMAINS.items():
        expected_stems[kind] = {
            orientation
            for pair_key in pairs
            if pair_key != "outer-planet-intensity"
            for orientation in pair_orientations(kind, pair_key)
        }
        actual_stems = set(PAIR_STEMS[kind])
        if actual_stems != expected_stems[kind]:
            errors.append(
                f"{kind} stem domain mismatch: missing={sorted(expected_stems[kind] - actual_stems)} "
                f"extra={sorted(actual_stems - expected_stems[kind])}"
            )

    for attraction_key, attraction_template in ATTRACTION_STEMS.items():
        attraction_text = attraction_template.format(actor="你", receiver="他")
        for friction_key, friction_template in FRICTION_STEMS.items():
            friction_text = friction_template.format(actor="你", receiver="他")
            shared_prefix = 0
            for attraction_character, friction_character in zip(
                attraction_text,
                friction_text,
            ):
                if attraction_character != friction_character:
                    break
                shared_prefix += 1
            if shared_prefix >= 7:
                errors.append(
                    "relationship body repeats attraction/friction opening: "
                    f"{attraction_key}/{friction_key}:{shared_prefix}"
                )

    all_copy: list[tuple[str, str]] = []
    all_copy.extend((f"headline:{key}", text) for key, text in ARCHETYPE_HEADLINES.items())
    all_copy.extend(
        (f"paragraph-thesis:{key}", text)
        for key, text in FIT_PARAGRAPH_THESES.items()
    )
    all_copy.extend(
        (f"paragraph-secondary-copy:{key}", text)
        for key, text in FIT_PARAGRAPH_SECONDARIES.items()
    )
    all_copy.extend(
        (f"paragraph-unknown-signal:{key}", text)
        for key, text in FIT_PARAGRAPH_UNKNOWN_SIGNALS.items()
    )
    all_copy.extend(
        (
            f"paragraph-secondary:{value_key}",
            paragraph_relationship_fit_value("secondary-dynamic", value_key),
        )
        for value_key in SECONDARY_DYNAMIC_FORMS
    )
    for role, catalog in (
        ("primary-dynamic", PRIMARY_DYNAMIC_FORMS),
        ("secondary-dynamic", SECONDARY_DYNAMIC_FORMS),
        *UNKNOWN_SIGNAL_FORMS.items(),
    ):
        for value_key, entry in (
            catalog.items() if isinstance(catalog, dict) else (("unknown", catalog),)
        ):
            for purpose in REALIZATION_PURPOSES:
                all_copy.append(
                    (f"{role}:{value_key}:{purpose}", entry.forms.for_purpose(purpose))
                )
    for role, kind in ROLE_TO_KIND.items():
        for value_key in supported_signal_values(kind):
            forms = signal_forms(value_key, expected_kind=kind)
            try:
                forms.validate(f"{role}:{value_key}")
            except ValueError as exc:
                errors.append(str(exc))
            for purpose in REALIZATION_PURPOSES:
                all_copy.append(
                    (
                        f"{role}:{value_key}:{purpose}",
                        forms.for_purpose(purpose),
                    )
                )
            all_copy.append(
                (
                    f"paragraph-{role}:{value_key}",
                    paragraph_relationship_fit_value(role, value_key),
                )
            )
        all_copy.append(
            (
                f"paragraph-{role}:unknown",
                paragraph_relationship_fit_value(
                    role,
                    f"{kind}:{kind}dynamics:unresolved",
                ),
            )
        )
    all_copy.append(("fit-boundary", FIT_BOUNDARY))

    for identity, text in all_copy:
        issues = audit_native_zh_tw_text(text)
        if issues:
            errors.append(
                f"{identity}: native Chinese issues: "
                + ", ".join(issue.id for issue in issues)
            )
        hits = [
            phrase for phrase in RELATIONSHIP_FIT_FORBIDDEN_REGRESSIONS if phrase in text
        ]
        if hits:
            errors.append(f"{identity}: reader regression returned: {hits}")

    try:
        traces = relationship_fit_sentence_traces()
    except RelationshipFitNativeChineseError as exc:
        errors.append(str(exc))
    else:
        for normalized, trace in traces.items():
            if not normalized:
                errors.append(f"empty traced relationship-fit sentence: {trace}")
    return errors


__all__ = [
    "ARCHETYPE_HEADLINES",
    "CANONICAL_POLARITY",
    "FIT_BOUNDARY",
    "FIT_PARAGRAPH_THESES",
    "FIT_PARAGRAPH_SECONDARIES",
    "FIT_PARAGRAPH_UNKNOWN_SIGNALS",
    "PRIMARY_DYNAMIC_FORMS",
    "RELATIONSHIP_FIT_FORBIDDEN_REGRESSIONS",
    "RELATIONSHIP_FIT_NATIVE_ZH_TW_CATALOG_VERSION",
    "ROLE_TO_KIND",
    "SECONDARY_DYNAMIC_FORMS",
    "UNKNOWN_SIGNAL_FORMS",
    "RelationshipFitNativeChineseError",
    "catalog_errors",
    "caution_for",
    "finish_sentence",
    "headline_for",
    "paragraph_relationship_fit_frame",
    "paragraph_relationship_fit_value",
    "realize_relationship_fit_frame",
    "relationship_fit_sentence_trace",
    "signal_forms",
    "supported_signal_values",
    "validate_relationship_fit_rendered",
]
