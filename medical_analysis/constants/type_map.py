# Маппинг параметров на их реальные типы анализов
from medical_analysis.enums import AnalysisType

PARAMETER_TYPE_MAP = {
    # ОАК
    "hemoglobin": AnalysisType.BLOOD_GENERAL,
    "hgb": AnalysisType.BLOOD_GENERAL,
    "hb": AnalysisType.BLOOD_GENERAL,
    "erythrocytes": AnalysisType.BLOOD_GENERAL,
    "rbc": AnalysisType.BLOOD_GENERAL,
    "leukocytes": AnalysisType.BLOOD_GENERAL,
    "wbc": AnalysisType.BLOOD_GENERAL,
    "platelets": AnalysisType.BLOOD_GENERAL,
    "plt": AnalysisType.BLOOD_GENERAL,
    "hematocrit": AnalysisType.BLOOD_GENERAL,
    "hct": AnalysisType.BLOOD_GENERAL,
    "esr": AnalysisType.BLOOD_GENERAL,
    "neutrophils": AnalysisType.BLOOD_GENERAL,
    "neutrophils_percentage": AnalysisType.BLOOD_GENERAL,
    "lymphocytes": AnalysisType.BLOOD_GENERAL,
    "lymphocytes_percentage": AnalysisType.BLOOD_GENERAL,
    "monocytes": AnalysisType.BLOOD_GENERAL,
    "monocytes_percentage": AnalysisType.BLOOD_GENERAL,
    "eosinophils": AnalysisType.BLOOD_GENERAL,
    "eosinophils_percentage": AnalysisType.BLOOD_GENERAL,
    "basophils": AnalysisType.BLOOD_GENERAL,
    "basophils_percentage": AnalysisType.BLOOD_GENERAL,
    "mcv": AnalysisType.BLOOD_GENERAL,
    "mch": AnalysisType.BLOOD_GENERAL,
    "mchc": AnalysisType.BLOOD_GENERAL,

    # Биохимия
    "glucose": AnalysisType.BLOOD_BIOCHEM,
    "creatinine": AnalysisType.BLOOD_BIOCHEM,
    "urea": AnalysisType.BLOOD_BIOCHEM,
    "alt": AnalysisType.BLOOD_BIOCHEM,
    "ast": AnalysisType.BLOOD_BIOCHEM,
    "bilirubin_total": AnalysisType.BLOOD_BIOCHEM,
    "cholesterol": AnalysisType.BLOOD_BIOCHEM,
    "atherogenic_index": AnalysisType.BLOOD_BIOCHEM,
    "gfr_ckd_epi": AnalysisType.BLOOD_BIOCHEM,

    # Гормоны
    "tsh": AnalysisType.HORMONES,
    "free_t4": AnalysisType.HORMONES,
    "free_t3": AnalysisType.HORMONES,
    "testosterone": AnalysisType.HORMONES,
    "estradiol": AnalysisType.HORMONES,
    "prolactin": AnalysisType.HORMONES,
    "cortisol": AnalysisType.HORMONES,
    "psa": AnalysisType.HORMONES,
}


