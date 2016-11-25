from __future__ import division

import urllib

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from django.template.defaultfilters import floatformat

from scorecard.utils import ratio


register = template.Library()


# about the same as similar municipalities in Western Cape: R123 123 123
# about half of the figure for similar municipalities nationally: R456 456 456
RELATIVE_PHRASE_MAP = {
    206: ["more than double", "the {0} for"],
    195: ["about double", "the {0} for"],
    180: ["nearly double", "the {0} for"],
    161: ["more than 1.5 times", "the {0} for"],
    145: ["about 1.5 times", "the {0} for"],
    135: ["about 1.4 times", "the {0} for"],
    128: ["about 1.3 times", "the {0} for"],
    122: ["about 25 percent higher", "than"],
    115: ["about 20 percent higher", "than"],
    107: ["about 10 percent higher", "than"],
    103: ["a little higher", "than"],
    98: ["about the same as", ""],
    94: ["a little less", "than"],
    86: ["about 90 percent", "of the {0} for"],
    78: ["about 80 percent", "of the {0} for"],
    72: ["about three-quarters", "of the {0} for"],
    64: ["about two-thirds", "of the {0} for"],
    56: ["about three-fifths", "of the {0} for"],
    45: ["about half", "of the {0} for"],
    37: ["about two-fifths", "of the {0} for"],
    30: ["about one-third", "of the {0} for"],
    23: ["about one-quarter", "of the {0} for"],
    17: ["about one-fifth", "of the {0} for"],
    13: ["less than a fifth", "of the {0} for"],
    8: ["about 10 percent", "of the {0} for"],
    0: ["less than 10 percent", "of the {0} for"],
}
RELATIVE_PHRASE_THRESHOLDS = sorted([k for k, v in RELATIVE_PHRASE_MAP.iteritems()])


# about two thirds of similar municipalities nationally [in Gauteng] have a positive cash balance
# no similar municipalities nationally [in Mpumalanga] have a positive cash balance
PERCENTAGE_PHRASE_MAP = {
    100: ["all", ""],
    94: ["almost all", ""],
    86: ["about 90 percent", "of"],
    78: ["about 80 percent", "of"],
    72: ["about three-quarters", "of"],
    64: ["about two-thirds", "of"],
    56: ["about three-fifths", "of"],
    45: ["about half", "of"],
    37: ["about two-fifths", "of"],
    30: ["about one-third", "of"],
    23: ["about one-quarter", "of"],
    17: ["about one-fifth", "of"],
    13: ["less than a fifth", "of"],
    8: ["about 10 percent", "of"],
    1: ["less than 10 percent", "of"],
    0: ["no", ""],
}
PERCENTAGE_PHRASE_THRESHOLDS = sorted([k for k, v in PERCENTAGE_PHRASE_MAP.iteritems()])


@register.simple_tag(takes_context=True)
def table_url(context, cube, year=None, muni=None, items=None, amountType=None):
    if not muni:
        muni = context['geography'].geo_code

    params = {
        "municipalities": muni,
    }
    if year:
        params["year"] = year
    if items:
        params["items"] = items
    if amountType:
        params["amountType"] = amountType

    for k, v in params.iteritems():
        if isinstance(v, list):
            params[k] = ",".join(v)

    return settings.API_BASE + "/table/" + cube + "/?" + urllib.urlencode(params)


@register.filter
def finyear(year):
    if year:
        year = int(year)
        return 'July %s - June %s' % (year - 1, year)
    return ''


@register.filter
def absolute(result):
    if result is not None:
        return abs(result)


@register.filter
def month_days(n):
    # months if >= 1, else days
    if n is None:
        return None

    if n < 1.0:
        return "%d days" % (n * 30)
    else:
        return "%.2g months" % n


@register.filter
def formatvalue(n, typ):
    if typ == 'currency' or typ == 'R':
        return u"R\u00A0" + floatformat(n, "0")

    if typ == 'months':
        return month_days(n)

    if typ == 'p' or typ == 'percent' or typ == '%':
        return str(n) + '%'

    if typ == 'ratio':
        return n

    return n


@register.inclusion_tag('profile/_comparative_list.html', takes_context=True)
def render_comparatives(context, indicator_name, result, result_type=None, noun='figure'):
    # about the same as similar municipalities in Western Cape: R123 123 123
    # about half of the figure for similar municipalities nationally: R456 456 456
    # about two thirds of similar municipalities nationally [in Gauteng] have a positive cash balance
    # no similar municipalities nationally [in Mpumalanga] have a positive cash balance
    geo = context['geography']
    medians = context['medians']
    indicator = context['indicators'][indicator_name]
    indicator['noun'] = noun
    date = str(result['date'])

    # XXX
    actual_medians = context.get('medians')
    import random
    def faker():
        return {
            'province': {'dev_cat': defaultdict(lambda: random.randint(100, 100000))},
            'national': actual_medians[indicator_name]['national'],
        }
    from collections import defaultdict
    medians = defaultdict(faker)

    item_context = {
        'indicator': indicator,
        'latest': result,
        'comparisons': [
            {
                'type': 'relative',
                'place': 'similar municipalities in ' + geo.province_name,
                'value': medians[indicator_name]['province']['dev_cat'][date],
                'value_type': result_type,
                'comparison': comparison_relative_words(result['result'], medians[indicator_name]['province']['dev_cat'][date], noun),
            },
            {
                'type': 'relative',
                'place': 'similar municipalities nationally',
                'value': medians[indicator_name]['national']['dev_cat'][date],
                'value_type': result_type,
                'comparison': comparison_relative_words(result['result'], medians[indicator_name]['national']['dev_cat'][date], noun),
            },
            # {
            #     'type': 'norm',
            #     'place': 'similar municipalities in Western Cape',
            #     'result': 0.55,
            # },
            # {
            #     'type': 'norm',
            #     'place': 'similar municipalities nationally',
            #     'result': 0.55,
            # },
        ],
    }
    return item_context


@register.filter
def comparison_relative_words(a, b, noun):
    """ Express the ratio +a/b+ as relative comparison between two places.

    The RELATIVE_PHRASE_MAP defines the comparative phrases; the dict keys
    are the lower boundary of the range of values that result in that phrase.

    For example, the effective range of index values that return the phrase
    "about half" would be 45 to 55.
    """
    if b == 0:
        # a/b == infinity
        phrase_bits = ["more than", "the {0} for"]
    else:
        # make sure we have an int for comparison
        index = abs(round(float(a / b) * 100))

        # get highest boundary that's less than the index value we've been passed
        phrase_key = max(k for k in RELATIVE_PHRASE_THRESHOLDS if k <= index)

        phrase_bits = RELATIVE_PHRASE_MAP[phrase_key]

    phrase = "<strong>%s</strong> %s" % (phrase_bits[0], phrase_bits[1].format(noun))
    return mark_safe(phrase)


@register.filter
def comparison_percentage_words(value):
    """ Express +value+, which is a value from [0, 1.0],
    as relative comparison between two places.

    The PERCENTAGE_PHRASE_MAP defines the comparative phrases; the dict keys
    are the lower boundary of the range of values that result in that phrase.

    For example, the effective range of index values that return the phrase
    "about half" would be 45 to 55.
    """
    # make sure we have an int for comparison
    index = round(float(value) * 100)

    # get highest boundary that's less than the index value we've been passed
    phrase_key = max(k for k in PERCENTAGE_PHRASE_THRESHOLDS if k <= index)

    phrase_bits = PERCENTAGE_PHRASE_MAP[phrase_key]
    phrase = "<strong>%s</strong> %s" % (phrase_bits[0], phrase_bits[1])
    return mark_safe(phrase)
