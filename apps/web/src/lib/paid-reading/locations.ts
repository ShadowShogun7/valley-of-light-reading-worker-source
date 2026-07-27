export const supportedBirthPlaces = [
  { label: "台北", value: "taipei" },
  { label: "新北", value: "new taipei" },
  { label: "桃園", value: "taoyuan" },
  { label: "新竹", value: "hsinchu" },
  { label: "台中", value: "taichung" },
  { label: "台南", value: "tainan" },
  { label: "高雄", value: "kaohsiung" },
  { label: "香港", value: "hong kong" },
  { label: "新加坡", value: "singapore" },
  { label: "東京", value: "tokyo" },
  { label: "首爾", value: "seoul" },
] as const;

const acceptedBirthPlaceValues = new Set<string>([
  ...supportedBirthPlaces.map((place) => place.value),
  "taipei city",
  "new taipei city",
  "taoyuan city",
  "hsinchu city",
  "taichung city",
  "tainan city",
  "kaohsiung city",
  "台北",
  "台北市",
  "臺北",
  "臺北市",
  "新北",
  "新北市",
  "桃園",
  "桃園市",
  "新竹",
  "新竹市",
  "台中",
  "台中市",
  "臺中",
  "臺中市",
  "台南",
  "台南市",
  "臺南",
  "臺南市",
  "高雄",
  "高雄市",
  "香港",
  "新加坡",
  "東京",
  "首爾",
]);

export function isSupportedBirthPlace(value: string) {
  const normalized = value.trim().toLowerCase();
  return normalized.length === 0 || acceptedBirthPlaceValues.has(normalized);
}
