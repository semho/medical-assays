"""
i18n helper utilities for medical analysis parameters
"""

from django.utils.translation import gettext as _, get_language


def get_parameter_display_name(param_key: str, unit: str = None) -> str:
    """
    get display name for medical parameter with proper i18n support

    uses name_key for english and names_ru for russian

    args:
        param_key: parameter key from PARAMETERS constant
        unit: unit of measurement (optional)

    returns:
        translated parameter name with suffix if applicable
    """
    from medical_analysis.constants.parameters import PARAMETERS

    param = PARAMETERS.get(param_key)
    if not param:
        return param_key

    # determine current language
    current_lang = get_language()

    # get base name based on language
    if current_lang == "ru":
        # russian - use names_ru
        base_name = param.get("names_ru", [param_key])[0]
    else:
        # english or other - use name_key
        name_key = param.get("name_key", param_key)
        # capitalize first letter for english
        base_name = name_key.title() if name_key else param_key

    # add suffix if unit matches display_suffix
    display_suffix = param.get("display_suffix")
    if display_suffix and unit and unit.strip() == display_suffix.strip():
        # remove suffix from base_name if it's already there
        if display_suffix in base_name:
            base_name = base_name.replace(display_suffix, "").strip()
        return f"{base_name} {display_suffix}"

    return base_name


def get_analysis_type_display(analysis_type: str) -> str:
    """
    get translated display name for analysis type

    args:
        analysis_type: analysis type code

    returns:
        translated analysis type name
    """
    type_map = {
        "blood_general": _("blood general"),
        "blood_biochem": _("blood biochem"),
        "hormones": _("hormones"),
        "other": _("other"),
    }
    return type_map.get(analysis_type, analysis_type)

def get_subscription_type_display(subscription_type: str) -> str:
    """
    get translated display name for subscription type

    args:
        subscription_type: subscription type code

    returns:
        translated subscription type name
    """
    type_map = {
        "trial": _("триал"),
        "paid": _("оплачен"),
    }
    return type_map.get(subscription_type, type_map)


def get_status_display(status: str) -> str:
    """
    get translated display name for processing status

    args:
        status: status code

    returns:
        translated status name
    """
    status_map = {
        "uploading": _("uploading"),
        "processing": _("processing"),
        "ocr": _("ocr"),
        "parsing": _("parsing"),
        "completed": _("completed"),
        "error": _("error"),
    }
    return status_map.get(status, status)


def get_laboratory_display(laboratory: str) -> str:
    """
    get translated display name for laboratory

    args:
        laboratory: laboratory code

    returns:
        translated laboratory name
    """
    lab_map = {
        "invitro": _("invitro"),
        "helix": _("helix"),
        "kdl": _("kdl"),
        "gemotest": _("gemotest"),
        "cmd": _("cmd"),
        "citilab": _("citilab"),
        "unknown": _("unknown"),
    }
    return lab_map.get(laboratory, laboratory)