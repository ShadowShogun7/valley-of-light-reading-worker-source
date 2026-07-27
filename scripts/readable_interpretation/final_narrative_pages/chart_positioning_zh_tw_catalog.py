"""Approved native Traditional Chinese catalog for chart positioning."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Literal, Mapping

from ..final_narrative_chinese_contract import audit_native_zh_tw_text
from ..final_narrative_chinese_plan import ReaderMeaningFrame
from ..final_narrative_realization import REALIZATION_PURPOSES, RealizationForms
from ..final_narrative_semantic_domains import ZODIAC_SIGNS


CHART_POSITIONING_NATIVE_ZH_TW_CATALOG_VERSION = "chart-positioning-native-zh-tw-catalog-v2"
CHART_POSITIONING_EXPECTED_APPROVED_FORM_COUNT = 117
ApprovalStatus = Literal["approved"]


class ChartPositioningNativeChineseError(ValueError):
    """Raised when chart-positioning copy is unapproved or unnatural."""


@dataclass(frozen=True)
class ApprovedRealizationForms:
    forms: RealizationForms
    status: ApprovalStatus = "approved"


def approved(direct: str, situational: str, relational: str) -> ApprovedRealizationForms:
    return ApprovedRealizationForms(RealizationForms(direct, situational, relational))


MOON_NATIVE_FORMS = {
    "moon.aries": approved(
        "你需要對方直接回應，等太久會讓你更不安",
        "事情一直沒有說開時，你會很想立刻確認答案",
        "對方願意坦白回應，你才比較能放下心裡的猜測",
    ),
    "moon.taurus": approved(
        "你重視穩定，答應的事有做到才會真正安心",
        "相處出現變化時，你會先看對方是否仍然可靠",
        "持續而實際的陪伴，比一時熱情更能讓你信任",
    ),
    "moon.gemini": approved(
        "你需要有來有往的對話，能聊下去才容易靠近",
        "聯絡突然停下來時，你心裡很容易冒出各種猜測",
        "對方願意接住話題，你會在交流中慢慢整理感受",
    ),
    "moon.cancer": approved(
        "你需要被在意，對方記得小事會讓你感到安心",
        "對方忽冷忽熱時，你會很快察覺並先保護自己",
        "熟悉而溫和的回應，會讓你更願意說出真正感受",
    ),
    "moon.leo": approved(
        "你需要感覺自己被重視，也希望付出有被看見",
        "對方明確肯定你時，你會更自然地表達喜歡",
        "長時間感覺被忽略，你容易先收起真正的需要",
    ),
    "moon.virgo": approved(
        "你會從日常細節確認對方是否可靠",
        "答應的事反覆沒有做到時，你會比聽到重話更不安",
        "對方把小事處理妥當，你才會逐漸建立信任",
    ),
    "moon.libra": approved(
        "你希望彼此願意商量，兩個人都有表達的空間",
        "只有一方做決定時，你會慢慢失去靠近的意願",
        "對話保有尊重和餘地，你才比較能安心說出不同意見",
    ),
    "moon.scorpio": approved(
        "你需要真誠和深度信任，表面的安撫很難讓你放心",
        "對方的回答含糊時，你會特別留意是否還有隱瞞",
        "關係越重要，你越需要確認彼此是否真的坦白",
    ),
    "moon.sagittarius": approved(
        "你希望兩個人坦白說清楚對未來的想法，也保有自己的生活",
        "相處讓你覺得被限制時，你會先拉開距離找回自己的空間",
        "彼此既能說真話又尊重自由，你才會自然地靠近",
    ),
    "moon.capricorn": approved(
        "你重視責任和長期可靠，不會只憑一時熱情放心",
        "對方只給口頭保證時，你會繼續觀察他是否做到",
        "看見對方持續承擔，你才會慢慢交付信任",
    ),
    "moon.aquarius": approved(
        "你需要被尊重，也希望保有自己的思考空間",
        "情緒壓力太強時，你會先拉開距離整理想法",
        "彼此能像朋友一樣平靜交談，你反而更願意親近",
    ),
    "moon.pisces": approved(
        "你很容易感受到氣氛，需要溫柔而真誠的回應",
        "對方情緒很重時，你可能不知不覺把感受全攬過來",
        "界線說得清楚，你才比較能安心付出而不被淹沒",
    ),
    "moon.unknown": approved(
        "目前資料不足，先從實際相處確認什麼會讓你安心",
        "出生資料不足時，先留意哪些互動會讓你放鬆或不安",
        "你需要怎樣的安全感，要用一段時間的真實相處確認",
    ),
}


MOON_PARAGRAPH_OPENINGS = {
    "moon.aries": "關係變得不確定時，你會想直接得到回應，答案懸著反而更難安心",
    "moon.taurus": "關係出現變化時，你會先看對方是否仍然可靠，實際做到比口頭保證更重要",
    "moon.gemini": "聯絡忽然停下時，你會想透過對話弄清楚發生了什麼，有來有往才比較安心",
    "moon.cancer": "對方的態度一變，你很快就會察覺，也會先確認自己是否仍被在意",
    "moon.leo": "你需要感覺自己的付出有被看見，對方明確重視你時才比較敢放心靠近",
    "moon.virgo": "你會從日常細節判斷一個人是否可靠，答應的事有沒有做到尤其重要",
    "moon.libra": "你希望兩個人願意商量，也都保有表達的空間，只有一方決定會讓你慢慢退開",
    "moon.scorpio": "關係越重要，你越需要真誠和深度信任，含糊的回答很難真正讓你放心",
    "moon.sagittarius": "關係變得不確定時，你會想坦白談清楚，也希望兩個人仍能保有自己的生活",
    "moon.capricorn": "你重視責任和長期可靠，只有看見對方持續做到，才會慢慢交付信任",
    "moon.aquarius": "你需要被尊重，也需要保有自己的思考空間，壓力太強時會先拉開一點距離",
    "moon.pisces": "你很容易感受到兩個人之間的氣氛，需要溫柔而清楚的回應才不會把情緒全攬過來",
    "moon.unknown": "目前還看不出你最需要哪一種安全感，要從真實相處確認什麼會讓你放鬆",
}


MERCURY_NATIVE_FORMS = {
    "mercury.aries": approved(
        "你談重要事情時很直接，希望問題不要一直拖著",
        "對方遲遲沒有回應時，你的語氣容易變得更急",
        "對方需要時間思考時，你們很容易卡在不同速度",
    ),
    "mercury.taurus": approved(
        "你需要先想清楚，再把自己的立場說出來",
        "對方反覆改口時，你會更難相信這次談話有結果",
        "把做法說得明確，你才比較願意繼續往下談",
    ),
    "mercury.gemini": approved(
        "你常在說話的過程中整理想法，也會想到新的角度",
        "對話突然停住時，你容易在心裡補出更多問題",
        "對方願意來回討論，你會越說越接近真正重點",
    ),
    "mercury.cancer": approved(
        "你很在意對方說話的口氣，先被理解才說得下去",
        "語氣一變重，你容易先收起真正想說的話",
        "對方先接住你的感受，你才更容易把事情說清楚",
    ),
    "mercury.leo": approved(
        "你表達時有明確立場，也需要對方認真聽完",
        "感覺被否定時，你的語氣和立場都容易變硬",
        "對方尊重你的表達，你才願意說出比較柔軟的一面",
    ),
    "mercury.virgo": approved(
        "你會把問題一項一項說清楚，也很在意細節是否正確",
        "你急著修正說法時，對方有時會聽成你在挑錯",
        "先說明你想解決什麼，細節才不容易變成新的壓力",
    ),
    "mercury.libra": approved(
        "有分歧時，你會先找兩邊都能接受的說法",
        "對方逼你當場選邊時，你很難直接說出真正想法",
        "對話保留尊重和餘地，你才比較能坦白表達不同意見",
    ),
    "mercury.scorpio": approved(
        "你想談到真正原因，不喜歡用幾句好聽話帶過",
        "對方回答含糊時，你會一直追問話背後的意思",
        "對方願意坦白說明，你才會停止反覆猜測",
    ),
    "mercury.sagittarius": approved(
        "你喜歡直接談大方向，不想繞開真正的問題",
        "覺得自己的看法被限制時，你說話會變得更直",
        "彼此容得下不同意見，你才願意把方向談清楚",
    ),
    "mercury.capricorn": approved(
        "你談重要事情時，會先確認做法、責任和可能的後果",
        "遇到問題時，你先想怎麼處理，對方若還在說感受，你們很容易各說各話",
        "對方提出具體做法時，你會更願意相信問題真的能處理",
    ),
    "mercury.aquarius": approved(
        "你需要先整理想法，才願意回答重要問題",
        "對方催你當場表態時，你反而更難把意思說完整",
        "有一點思考空間，你會更願意回來把話說清楚",
    ),
    "mercury.pisces": approved(
        "對方的語氣和當下氣氛，很容易影響你怎麼表達",
        "氣氛混亂時，你可能先順著對方，沒有說清自己的想法",
        "對方說得溫和又具體，你才比較能表達真正感受",
    ),
    "mercury.unknown": approved(
        "目前資料不足，還不能從星盤確認你的表達習慣",
        "出生資料不足時，先看哪些說法最容易讓彼此誤會",
        "你們怎麼說、怎麼聽，需要從真實對話慢慢確認",
    ),
}


PRESSURE_NATIVE_FORMS = {
    "mars.aries": approved(
        "他有壓力時容易沒聽完就先做決定",
        "話題突然變重時，他容易立刻回話或直接採取行動",
        "你越急著把話說完，他越容易沒聽完就先回話，兩個人都來不及聽懂",
    ),
    "mars.taurus": approved(
        "他有壓力時會守住原本立場，不想先退一步",
        "爭執剛開始時，他可能一直重複同一個說法",
        "你越要求他立刻改口，他越容易把立場守得更緊",
    ),
    "mars.gemini": approved(
        "他有壓力時容易越說越多，把一件事拉出很多支線",
        "話題一變重，他可能同時提出好幾個新的問題",
        "你越追著每個細節問，他越容易把真正重點說散",
    ),
    "mars.cancer": approved(
        "他感覺被責怪時，會先保護自己，很難立刻談下去",
        "現在的話碰到以前的不舒服時，他容易先縮回去",
        "你越急著確認，他越容易想起過去的不愉快並開始防備",
    ),
    "mars.leo": approved(
        "他感覺被否定時，會先維護自尊，很難繼續聽下去",
        "討論開始像在分輸贏時，他容易把重點放在保護自己",
        "你越想證明自己的道理，他越容易覺得自己沒有被尊重",
    ),
    "mars.virgo": approved(
        "他有壓力時會抓住字句和對錯，想把問題立刻修正",
        "兩個人開始挑彼此說法時，他容易忘記原本在意什麼",
        "你越要求每句話都說對，他越容易卡在細節裡出不來",
    ),
    "mars.libra": approved(
        "他有壓力時可能先忍著，累積久了才突然說重話",
        "他從沉默變得強硬時，通常已經把不滿放了一段時間",
        "你以為他的沉默代表沒事，他卻可能一直把不舒服留在心裡",
    ),
    "mars.scorpio": approved(
        "事情碰到信任時，他的反應容易變得特別強烈",
        "他懷疑自己被隱瞞時，一件小事也可能被聽得很重",
        "你越猜測他的動機，他越容易保護自己並停止坦白",
    ),
    "mars.sagittarius": approved(
        "他感覺被限制時，容易反抗或直接離開談話",
        "被要求立刻表態時，他可能先結束對話來保留空間",
        "你越想限制他的選擇，他越容易用拉開距離來回應",
    ),
    "mars.capricorn": approved(
        "他有壓力時會先考慮責任和後果，回應可能因此變慢",
        "一談到長期承諾，他會先衡量自己是否真的做得到",
        "你越要求他當場承諾，他越容易退回現實考量並保持沉默",
    ),
    "mars.aquarius": approved(
        "情緒太重時，他會先拉開距離整理自己",
        "被要求當場回答時，他可能先離開對話讓自己冷靜",
        "你越急著把他拉回情緒裡，他越需要更多空間",
    ),
    "mars.pisces": approved(
        "很多感受同時出現時，他容易沉默或退回自己的情緒",
        "話題一次變得太多時，他可能不知道該先回應哪一件事",
        "你越希望他一次接住所有感受，他越容易停在沉默裡",
    ),
    "mars.unknown": approved(
        "目前資料不足，還不能從星盤確認他的壓力反應",
        "出生資料不足時，先看話題變重後他的回應有沒有縮短",
        "他有壓力時會靠近還是退開，需要從真實互動確認",
    ),
}


MERCURY_PARAGRAPH_FOLLOWUPS = {
    "mercury.aries": "遇到問題時，你會想立刻把話說開，不喜歡讓答案一直懸著",
    "mercury.taurus": "遇到問題時，你會先想清楚自己的立場，確認做法穩定後才願意往下談",
    "mercury.gemini": "遇到問題時，你會在對話裡整理想法，需要有來有往才比較能抓到重點",
    "mercury.cancer": "遇到問題時，你需要先感覺自己被理解，才比較說得出真正介意的事",
    "mercury.leo": "遇到問題時，你會清楚表達立場，也需要對方認真聽完而不是立刻否定",
    "mercury.virgo": "遇到問題時，你會從細節逐一確認，希望把事情整理到可以實際處理",
    "mercury.libra": "遇到問題時，你會先找雙方都能接受的說法，希望對話保有尊重和餘地",
    "mercury.scorpio": "遇到問題時，你會追問真正原因，含糊的回答反而讓你更難停止猜測",
    "mercury.sagittarius": "遇到問題時，你會直接談大方向，希望彼此不要繞開真正需要決定的事",
    "mercury.capricorn": "遇到問題時，你會先確認做法、責任和後果，因為有明確安排才會相信事情真的能處理",
    "mercury.aquarius": "遇到問題時，你需要先整理想法，有一點空間後才比較能把意思說完整",
    "mercury.pisces": "遇到問題時，你會先感受對方的語氣和氣氛，太混亂時反而不容易說清自己",
    "mercury.unknown": "目前還看不出你習慣怎麼處理分歧，需要從真實對話確認哪種說法最適合你",
}


PRESSURE_PARAGRAPH_CONTRASTS = {
    "mars.aries": "對方有壓力時可能還沒聽完就先回話或做決定",
    "mars.taurus": "對方在壓力下會先守住原本立場，需要時間才願意重新考慮",
    "mars.gemini": "對方在壓力下容易一次說很多事情，真正要處理的重點反而可能被說散",
    "mars.cancer": "對方感覺被責怪時會先保護自己，等不舒服降下來後才比較談得下去",
    "mars.leo": "對方感覺被否定時會先保護自尊，對話一像在分輸贏就很難繼續聽",
    "mars.virgo": "對方在壓力下會抓住字句和對錯，太多細節容易讓他忘記原本在意什麼",
    "mars.libra": "對方在壓力下可能先忍住不說，等累積太久後才突然用比較重的方式表達",
    "mars.scorpio": "對方碰到信任問題時反應會變得很強，需要先分清事實和彼此的猜測",
    "mars.sagittarius": "對方感覺被限制時會先離開談話，保有選擇空間後才比較願意回來談",
    "mars.capricorn": "對方在壓力下會先考慮責任和後果，確認自己做得到以前不容易立刻答應",
    "mars.aquarius": "對方在壓力下需要先拉開一點距離，等情緒降下來後才比較能回到對話",
    "mars.pisces": "對方同時接到太多感受時容易沉默，需要一次只面對一件事才比較能回應",
    "mars.unknown": "目前還看不出對方在壓力下會靠近還是退開，需要從話題變重後的反應確認",
}


MOON_NEED_GROUPS = {
    "moon.aries": "direct",
    "moon.gemini": "direct",
    "moon.sagittarius": "direct",
    "moon.taurus": "steady",
    "moon.virgo": "steady",
    "moon.capricorn": "steady",
    "moon.cancer": "sensitive",
    "moon.scorpio": "sensitive",
    "moon.pisces": "sensitive",
    "moon.leo": "respect",
    "moon.libra": "respect",
    "moon.aquarius": "respect",
    "moon.unknown": "unknown",
}

PRESSURE_GROUPS = {
    "mars.aries": "moves-first",
    "mars.gemini": "talks-more",
    "mars.leo": "protects-pride",
    "mars.taurus": "holds-ground",
    "mars.virgo": "holds-ground",
    "mars.capricorn": "holds-ground",
    "mars.cancer": "protects-self",
    "mars.sagittarius": "leaves-conversation",
    "mars.aquarius": "takes-space",
    "mars.pisces": "becomes-silent",
    "mars.libra": "intensifies",
    "mars.scorpio": "intensifies",
    "mars.unknown": "unknown",
}

CHART_HEADLINES = {
    ("direct", "moves-first"): "你想先談清楚，他有壓力時容易沒聽完就先回話",
    ("direct", "talks-more"): "你想把重點談清楚，他有壓力時卻容易把話題越拉越開",
    ("direct", "protects-pride"): "你想把話說清楚，他一覺得被否定就先維護自己的立場",
    ("direct", "holds-ground"): "你想先談清楚，他會先守住自己的立場",
    ("direct", "protects-self"): "你想先談清楚，他一覺得被責怪就很難繼續說下去",
    ("direct", "leaves-conversation"): "你想先談清楚，他一覺得被限制就容易結束對話",
    ("direct", "takes-space"): "你想先談清楚，他情緒太重時卻需要暫停對話",
    ("direct", "becomes-silent"): "你想先談清楚，他同時接到太多感受時卻容易沉默",
    ("direct", "intensifies"): "你想先談清楚，他的反應卻容易變強",
    ("steady", "moves-first"): "你重視可靠，他有壓力時卻容易急著做決定",
    ("steady", "talks-more"): "你重視可靠，他有壓力時卻容易同時談太多事情",
    ("steady", "protects-pride"): "你重視可靠，他一覺得被否定就容易把對話聽成輸贏",
    ("steady", "holds-ground"): "你重視穩定，他有壓力時先守住原本做法",
    ("steady", "protects-self"): "你需要可靠回應，他一覺得被責怪就很難繼續說下去",
    ("steady", "leaves-conversation"): "你重視可靠，他一覺得被限制就容易直接離開談話",
    ("steady", "takes-space"): "你需要可靠回應，他情緒太重時卻需要先安靜一下",
    ("steady", "becomes-silent"): "你需要可靠回應，他同時接到太多感受時卻容易沉默",
    ("steady", "intensifies"): "你想把事情做好，他的壓力容易累積",
    ("sensitive", "moves-first"): "你會先留意氣氛，他有壓力時卻容易沒聽完就先回話",
    ("sensitive", "talks-more"): "你會先留意氣氛，他有壓力時卻容易越說越多",
    ("sensitive", "protects-pride"): "你會先留意氣氛，他一覺得被否定就很難繼續聽",
    ("sensitive", "holds-ground"): "你需要被理解，他有壓力時先抓住立場",
    ("sensitive", "protects-self"): "你希望他理解你的感受，他一覺得被責怪就很難繼續說下去",
    ("sensitive", "leaves-conversation"): "你希望他溫和回應，他一覺得被限制就容易結束對話",
    ("sensitive", "takes-space"): "你希望他溫和回應，他情緒太重時卻需要暫停對話",
    ("sensitive", "becomes-silent"): "你希望他溫和回應，他同時接到太多感受時卻容易沉默",
    ("sensitive", "intensifies"): "你對反應很敏感，他的壓力也容易放大",
    ("respect", "moves-first"): "你在意彼此是否尊重，他有壓力時卻容易急著回話",
    ("respect", "talks-more"): "你在意彼此是否尊重，他有壓力時卻容易一次提出太多問題",
    ("respect", "protects-pride"): "你在意彼此是否尊重，他也很難接受自己被否定",
    ("respect", "holds-ground"): "你重視尊重，他有壓力時先守住立場",
    ("respect", "protects-self"): "你在意彼此是否尊重，他一覺得被責怪就會先保護自己",
    ("respect", "leaves-conversation"): "你需要彼此保有空間，他一覺得被限制就容易結束對話",
    ("respect", "takes-space"): "你也需要自己的空間，他情緒太重時同樣需要暫停對話",
    ("respect", "becomes-silent"): "你在意彼此是否尊重，他同時接到太多感受時卻容易沉默",
    ("respect", "intensifies"): "你在意是否被尊重，他的壓力容易累積",
    ("unknown", "moves-first"): "先看什麼讓你安心，也看他是否會急著回話或做決定",
    ("unknown", "talks-more"): "先看什麼讓你安心，也看他是否一有壓力就把話題說散",
    ("unknown", "protects-pride"): "先看什麼讓你安心，也看他被否定時能不能繼續聽",
    ("unknown", "holds-ground"): "先從相處確認你的需要和他的反應",
    ("unknown", "protects-self"): "先看什麼讓你安心，也看他被責怪時能不能繼續談",
    ("unknown", "leaves-conversation"): "先看什麼讓你安心，也看他覺得被限制時是否會結束對話",
    ("unknown", "takes-space"): "先看什麼讓你安心，也看他情緒太重時需要多久才願意再談",
    ("unknown", "becomes-silent"): "先看什麼讓你安心，也看他面對太多感受時是否會沉默",
    ("unknown", "intensifies"): "先從真實互動理解彼此的反應",
    ("direct", "unknown"): "你需要清楚回應，他的壓力反應仍要觀察",
    ("steady", "unknown"): "你重視可靠，他的壓力反應仍要觀察",
    ("sensitive", "unknown"): "你需要溫和回應，他的反應仍要觀察",
    ("respect", "unknown"): "你需要被尊重，他的壓力反應仍要觀察",
    ("unknown", "unknown"): "先從真實相處確認彼此的習慣",
}

PRESSURE_ACTIONS = {
    "mars.aries": "他還沒聽完就先回話時，先停一下，不要急著當場做決定",
    "mars.taurus": "他開始重複同一個立場時，先暫停，不再用更多理由逼他改口",
    "mars.gemini": "話題拉出太多支線時，先回到這次真正要處理的一件事",
    "mars.cancer": "他開始防備時，只談眼前這件事，不把以前的不愉快一起翻出來",
    "mars.leo": "對話變成輸贏時，先回到具體發生的事，不評價他整個人",
    "mars.virgo": "彼此開始挑字句時，先問真正介意的是哪一件事",
    "mars.libra": "他從沉默變得強硬時，先結束這次對話，等情緒回穩再談",
    "mars.scorpio": "話題碰到信任時，先分清已經發生的事和各自的猜測",
    "mars.sagittarius": "他想離開談話時，先給空間，不追著要求他表態",
    "mars.capricorn": "他開始考慮責任和後果時，先談一件現在做得到的安排",
    "mars.aquarius": "他先拉開距離時，不要連續追問，等他願意回到對話",
    "mars.pisces": "他被很多感受淹沒時，只留一件具體的事讓他回應",
    "mars.unknown": "還看不清他的壓力反應時，先縮短話題，不用追問測試",
}

PRECISION_CAUTIONS = {
    "chart-only": "這些是常見反應，真正怎麼相處仍要看兩個人的實際選擇",
    "full": "出生資料較完整，但這些傾向仍要用長期相處確認",
    "partial": "部分出生資料不完整，所以只保留目前能確認的基本習慣",
    "low": "出生資料有限，因此不延伸判斷更細的反應方式",
    "unknown": "出生資料不足，目前只保留能確認的相處習慣",
}

CHART_POSITIONING_FORBIDDEN_REGRESSIONS = (
    "理解彼此原本的親密關係節奏",
    "你希望關係能誠實談方向，也能保留各自的生活",
    "你先談做法和後果，才相信問題能處理；對方只談感覺時，你們容易各自錯過重點",
    "集中時，你的靠近和處理衝突的速度一明顯，他的表達好感的方式也會被帶動",
)

ROLE_CATALOGS: Mapping[str, Mapping[str, ApprovedRealizationForms]] = {
    "user-emotional-need": MOON_NATIVE_FORMS,
    "user-communication-style": MERCURY_NATIVE_FORMS,
    "partner-pressure-response": PRESSURE_NATIVE_FORMS,
}


def normalize_copy(value: str) -> str:
    return re.sub(r"[\s，。；：！？!?「」『』（）()、]", "", str(value or ""))


def finish_sentence(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip(" ，。；;\n")
    return f"{text}。" if text else ""


def realize_chart_frame(frame: ReaderMeaningFrame) -> str:
    frame.validate()
    if frame.section_id != "chart-positioning":
        raise ChartPositioningNativeChineseError(
            f"chart catalog received frame for {frame.section_id}"
        )
    catalog = ROLE_CATALOGS.get(frame.role)
    if catalog is None:
        raise ChartPositioningNativeChineseError(f"unsupported chart role: {frame.role}")
    entry = catalog.get(frame.value_key)
    if entry is None or entry.status != "approved":
        raise ChartPositioningNativeChineseError(
            f"unapproved chart realization: {frame.role}:{frame.value_key}"
        )
    entry.forms.validate(f"chart-native:{frame.role}:{frame.value_key}")
    return entry.forms.for_purpose(frame.purpose)


def paragraph_chart_frame(frame: ReaderMeaningFrame) -> str:
    frame.validate()
    if frame.role == "user-emotional-need":
        text = MOON_PARAGRAPH_OPENINGS.get(frame.value_key)
        if text is None:
            raise ChartPositioningNativeChineseError(
                f"missing chart paragraph opening: {frame.value_key}"
            )
        return text
    if frame.role == "user-communication-style":
        try:
            return MERCURY_PARAGRAPH_FOLLOWUPS[frame.value_key]
        except KeyError as exc:
            raise ChartPositioningNativeChineseError(
                f"missing chart paragraph followup: {frame.value_key}"
            ) from exc
    if frame.role == "partner-pressure-response":
        try:
            return PRESSURE_PARAGRAPH_CONTRASTS[frame.value_key]
        except KeyError as exc:
            raise ChartPositioningNativeChineseError(
                f"missing chart paragraph contrast: {frame.value_key}"
            ) from exc
    raise ChartPositioningNativeChineseError(
        f"unsupported chart paragraph role: {frame.role}"
    )


def headline_for(moon_value: str, pressure_value: str) -> str:
    need_group = MOON_NEED_GROUPS.get(moon_value)
    pressure_group = PRESSURE_GROUPS.get(pressure_value)
    headline = CHART_HEADLINES.get((str(need_group or ""), str(pressure_group or "")))
    if not headline:
        raise ChartPositioningNativeChineseError(
            f"missing chart headline: {moon_value}:{pressure_value}"
        )
    return headline


def action_for(pressure_value: str) -> str:
    action = PRESSURE_ACTIONS.get(pressure_value)
    if not action:
        raise ChartPositioningNativeChineseError(
            f"missing chart pressure action: {pressure_value}"
        )
    return action


def caution_for(precision_value: str) -> str:
    caution = PRECISION_CAUTIONS.get(precision_value)
    if not caution:
        raise ChartPositioningNativeChineseError(
            f"missing chart precision caution: {precision_value}"
        )
    return caution


@lru_cache(maxsize=1)
def catalog_sentence_traces() -> dict[str, dict[str, str]]:
    traces: dict[str, dict[str, str]] = {}

    def add(text: str, trace: dict[str, str]) -> None:
        normalized = normalize_copy(text)
        if normalized in traces and traces[normalized] != trace:
            raise ChartPositioningNativeChineseError(
                f"chart sentence has ambiguous trace: {text}"
            )
        traces[normalized] = trace

    for role, catalog in ROLE_CATALOGS.items():
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
    for value_key, text in MOON_PARAGRAPH_OPENINGS.items():
        add(
            text,
            {
                "kind": "paragraph-realization",
                "role": "user-emotional-need",
                "valueKey": value_key,
                "purpose": "direct",
            },
        )
    for value_key, text in MERCURY_PARAGRAPH_FOLLOWUPS.items():
        add(
            text,
            {
                "kind": "paragraph-realization",
                "role": "user-communication-style",
                "valueKey": value_key,
                "purpose": "situational",
            },
        )
    for value_key, text in PRESSURE_PARAGRAPH_CONTRASTS.items():
        add(
            text,
            {
                "kind": "paragraph-realization",
                "role": "partner-pressure-response",
                "valueKey": value_key,
                "purpose": "situational",
            },
        )
    for headline in CHART_HEADLINES.values():
        add(headline, {"kind": "composition", "role": "headline", "purpose": "composition"})
    for value_key, action in PRESSURE_ACTIONS.items():
        add(
            action,
            {
                "kind": "composition",
                "role": "partner-pressure-response",
                "valueKey": value_key,
                "purpose": "action",
            },
        )
    for value_key, caution in PRECISION_CAUTIONS.items():
        add(
            caution,
            {
                "kind": "composition",
                "role": "precision-mode",
                "valueKey": value_key,
                "purpose": "boundary",
            },
        )
    return traces


def chart_sentence_trace(text: str) -> dict[str, str] | None:
    return catalog_sentence_traces().get(normalize_copy(text))


def _assert_trace(
    text: str,
    *,
    kind: str,
    role: str,
    value_key: str = "",
    purpose: str,
) -> None:
    trace = chart_sentence_trace(text)
    expected = {
        "kind": kind,
        "role": role,
        "purpose": purpose,
    }
    if value_key:
        expected["valueKey"] = value_key
    if trace != expected:
        raise ChartPositioningNativeChineseError(
            f"untraceable chart sentence: expected={expected} actual={trace} text={text}"
        )


def validate_chart_positioning_rendered(
    rendered: Mapping[str, str],
    *,
    moon_frame: ReaderMeaningFrame,
    mercury_frame: ReaderMeaningFrame,
    pressure_frame: ReaderMeaningFrame,
    precision_frame: ReaderMeaningFrame,
) -> None:
    frames = (moon_frame, mercury_frame, pressure_frame, precision_frame)
    for frame in frames:
        frame.validate()
        if frame.section_id != "chart-positioning":
            raise ChartPositioningNativeChineseError(
                f"chart renderer received frame for {frame.section_id}"
            )
    expected_purposes = {
        "user-emotional-need": "direct",
        "user-communication-style": "situational",
        "partner-pressure-response": "situational",
        "precision-mode": "direct",
    }
    for frame in frames:
        expected_purpose = expected_purposes.get(frame.role)
        if frame.purpose != expected_purpose:
            raise ChartPositioningNativeChineseError(
                f"wrong chart realization purpose: {frame.role}:{frame.purpose}"
            )

    moon_text = paragraph_chart_frame(moon_frame)
    mercury_text = paragraph_chart_frame(mercury_frame)
    pressure_text = paragraph_chart_frame(pressure_frame)
    expected = {
        "headline": headline_for(moon_frame.value_key, pressure_frame.value_key),
        "meaning": finish_sentence(moon_text) + finish_sentence(mercury_text),
        "body": finish_sentence(pressure_text),
        "nextMove": finish_sentence(action_for(pressure_frame.value_key)),
        "caution": finish_sentence(caution_for(precision_frame.value_key)),
    }
    if dict(rendered) != expected:
        raise ChartPositioningNativeChineseError(
            "chart renderer output does not match its owned meaning frames"
        )

    for field, text in expected.items():
        issues = audit_native_zh_tw_text(text)
        if issues:
            details = ", ".join(f"{item.severity}:{item.id}" for item in issues)
            raise ChartPositioningNativeChineseError(
                f"chart-positioning:{field}: native Chinese gate failed: {details}"
            )
        regressions = [
            phrase
            for phrase in CHART_POSITIONING_FORBIDDEN_REGRESSIONS
            if phrase in text
        ]
        if regressions:
            raise ChartPositioningNativeChineseError(
                f"chart-positioning:{field}: reader regression returned: {regressions}"
            )

    meaning_sentences = [
        item.strip()
        for item in re.split(r"[。！？!?]+", expected["meaning"])
        if item.strip()
    ]
    if len(meaning_sentences) != 2:
        raise ChartPositioningNativeChineseError(
            "chart meaning must contain exactly two owned sentences"
        )
    _assert_trace(
        meaning_sentences[0],
        kind="paragraph-realization",
        role=moon_frame.role,
        value_key=moon_frame.value_key,
        purpose=moon_frame.purpose,
    )
    _assert_trace(
        meaning_sentences[1],
        kind="paragraph-realization",
        role=mercury_frame.role,
        value_key=mercury_frame.value_key,
        purpose=mercury_frame.purpose,
    )
    _assert_trace(
        pressure_text,
        kind="paragraph-realization",
        role=pressure_frame.role,
        value_key=pressure_frame.value_key,
        purpose=pressure_frame.purpose,
    )
    _assert_trace(
        expected["headline"],
        kind="composition",
        role="headline",
        purpose="composition",
    )
    _assert_trace(
        action_for(pressure_frame.value_key),
        kind="composition",
        role=pressure_frame.role,
        value_key=pressure_frame.value_key,
        purpose="action",
    )
    _assert_trace(
        caution_for(precision_frame.value_key),
        kind="composition",
        role=precision_frame.role,
        value_key=precision_frame.value_key,
        purpose="boundary",
    )

    similarity = SequenceMatcher(
        None,
        normalize_copy(moon_text),
        normalize_copy(mercury_text),
    ).ratio()
    if similarity >= 0.55:
        raise ChartPositioningNativeChineseError(
            f"chart meaning sentences collapse into the same thought: {similarity:.3f}"
        )


def catalog_errors() -> list[str]:
    errors: list[str] = []
    sign_values = {*ZODIAC_SIGNS, "unknown"}
    expected_domains = {
        "user-emotional-need": {f"moon.{sign}" for sign in sign_values},
        "user-communication-style": {f"mercury.{sign}" for sign in sign_values},
        "partner-pressure-response": {f"mars.{sign}" for sign in sign_values},
    }
    approved_count = 0
    all_copy: list[tuple[str, str]] = []
    for role, catalog in ROLE_CATALOGS.items():
        if set(catalog) != expected_domains[role]:
            errors.append(f"{role}: native catalog domain is incomplete")
        for value_key, entry in catalog.items():
            if entry.status != "approved":
                errors.append(f"{role}:{value_key}: realization is not approved")
            try:
                entry.forms.validate(f"{role}:{value_key}")
            except ValueError as exc:
                errors.append(str(exc))
            for purpose in REALIZATION_PURPOSES:
                approved_count += 1
                all_copy.append(
                    (f"{role}:{value_key}:{purpose}", entry.forms.for_purpose(purpose))
                )
    if approved_count != CHART_POSITIONING_EXPECTED_APPROVED_FORM_COUNT:
        errors.append(
            f"approved form count {approved_count} != "
            f"{CHART_POSITIONING_EXPECTED_APPROVED_FORM_COUNT}"
        )
    if set(MOON_NEED_GROUPS) != expected_domains["user-emotional-need"]:
        errors.append("Moon headline-group domain is incomplete")
    if set(MOON_PARAGRAPH_OPENINGS) != expected_domains["user-emotional-need"]:
        errors.append("Moon paragraph-opening domain is incomplete")
    if set(PRESSURE_GROUPS) != expected_domains["partner-pressure-response"]:
        errors.append("pressure headline-group domain is incomplete")
    expected_headline_pairs = {
        (need, pressure)
        for need in set(MOON_NEED_GROUPS.values())
        for pressure in set(PRESSURE_GROUPS.values())
    }
    if set(CHART_HEADLINES) != expected_headline_pairs:
        errors.append("chart headline combination domain is incomplete")
    if set(PRESSURE_ACTIONS) != expected_domains["partner-pressure-response"]:
        errors.append("pressure-action domain is incomplete")
    if set(MERCURY_PARAGRAPH_FOLLOWUPS) != expected_domains["user-communication-style"]:
        errors.append("Mercury paragraph domain is incomplete")
    if set(PRESSURE_PARAGRAPH_CONTRASTS) != expected_domains["partner-pressure-response"]:
        errors.append("pressure paragraph domain is incomplete")
    if set(PRECISION_CAUTIONS) != {"chart-only", "full", "partial", "low", "unknown"}:
        errors.append("precision-caution domain is incomplete")

    all_copy.extend(("headline", value) for value in CHART_HEADLINES.values())
    all_copy.extend(("moon-paragraph", value) for value in MOON_PARAGRAPH_OPENINGS.values())
    all_copy.extend(("mercury-paragraph", value) for value in MERCURY_PARAGRAPH_FOLLOWUPS.values())
    all_copy.extend(("pressure-paragraph", value) for value in PRESSURE_PARAGRAPH_CONTRASTS.values())
    all_copy.extend(("action", value) for value in PRESSURE_ACTIONS.values())
    all_copy.extend(("caution", value) for value in PRECISION_CAUTIONS.values())
    for identity, text in all_copy:
        issues = audit_native_zh_tw_text(text)
        if issues:
            errors.append(
                f"{identity}: native Chinese issues: "
                + ", ".join(issue.id for issue in issues)
            )
        hits = [phrase for phrase in CHART_POSITIONING_FORBIDDEN_REGRESSIONS if phrase in text]
        if hits:
            errors.append(f"{identity}: reader regression returned: {hits}")
    try:
        catalog_sentence_traces()
    except ChartPositioningNativeChineseError as exc:
        errors.append(str(exc))
    return errors


__all__ = [
    "CHART_HEADLINES",
    "CHART_POSITIONING_EXPECTED_APPROVED_FORM_COUNT",
    "CHART_POSITIONING_FORBIDDEN_REGRESSIONS",
    "CHART_POSITIONING_NATIVE_ZH_TW_CATALOG_VERSION",
    "MERCURY_NATIVE_FORMS",
    "MERCURY_PARAGRAPH_FOLLOWUPS",
    "MOON_NATIVE_FORMS",
    "MOON_PARAGRAPH_OPENINGS",
    "PRECISION_CAUTIONS",
    "PRESSURE_ACTIONS",
    "PRESSURE_PARAGRAPH_CONTRASTS",
    "PRESSURE_NATIVE_FORMS",
    "ChartPositioningNativeChineseError",
    "action_for",
    "catalog_errors",
    "chart_sentence_trace",
    "caution_for",
    "finish_sentence",
    "headline_for",
    "paragraph_chart_frame",
    "realize_chart_frame",
    "validate_chart_positioning_rendered",
]
