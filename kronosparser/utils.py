import re

import pyparsing


def find_all(expression, text):
    matches = []
    if expression is not None:
        for match in expression.scanString(text):
            # TODO(RA, 05-10-2016): find a method to prevent suppressed ParseResults objects from ever being created
            if len(match[0]) > 0:
                matches.append({
                    'text': text[match[1]:match[2]],
                    'parsed': match[0][0],
                    'start': match[1],
                    'end': match[2]
                })
    return matches


def caseless_literal_or(values):
    sorted_values = sorted(values, key=lambda x: (-len(x), x))
    return pyparsing.Regex('|'.join(re.escape(value) for value in sorted_values), re.IGNORECASE)


def _is_alphanumeric(value):
    return re.match('\w', value) is not None


def caseless_keyword(kw):
    leading = r'\b' if _is_alphanumeric(kw[0]) else ''
    trailing = r'\b' if _is_alphanumeric(kw[-1]) else ''
    return pyparsing.Regex('{}{}{}'.format(leading, re.escape(kw), trailing), re.IGNORECASE)


def caseless_keyword_or(values, no_lead=False, no_trail=False):
    sorted_values = sorted(values, key=lambda x: (-len(x), x))
    regexes = []
    for value in sorted_values:
        leading = r'\b'
        trailing = r'\b'
        if not _is_alphanumeric(value[0]) or no_lead:
            leading = ''
        if not _is_alphanumeric(value[-1]) or no_trail:
            trailing = ''
        regexes.append(re.escape(value))
    return pyparsing.Regex(r'{}({}){}'.format(leading, '|'.join(regexes), trailing), re.IGNORECASE)


def pluralize(words, pyparsing_regex=False):
    if isinstance(words, str):
        words = [words]
    if pyparsing_regex:
        return caseless_keyword_or(words + [plural(word) for word in words])
    else:
        return words + [plural(word) for word in words]


def plural(noun):
    if noun[-1] == 'y':
        if noun[-2] in 'aeiou':
            return noun + 's'
        return noun[:-1] + 'ies'
    if noun[-1] == 'f' and noun[-2] != 'f' and not all(
        [letter in 'aeiou' for letter in noun[-3:-1]]):
        return noun[:-1] + 'ves'
    if noun[-2:] == 'fe' and not all([letter in 'aeiou' for letter in noun[-4:-2]]):
        return noun[:-2] + 'ves'
    if noun[-1] in ['s', 'x', 'z'] or noun[-2:] in ['ch', 'sh']:
        return noun + 'es'
    return noun + 's'


def structurize(text, parsers):
    results = []
    for parser in parsers:
        results.extend(find_all(parser, text))
    return results
