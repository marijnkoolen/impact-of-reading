import json
import re
from Model.impact_model import impact_groups
#from Model.impact_model import impact_contexts

CONTEXT_LENGTH = 10

def has_one_of_contexts(text, contexts, impact_term):
    for context in contexts:
        if has_context(text, context, impact_term):
            return True
    return False

def has_context(text, context, impact_term):
    for context_chunk in context:
        if "{IMPACT_TERM}" in context_chunk:
            context_chunk = context_chunk.replace("{IMPACT_TERM}", impact_term)
        if not re.search(context_chunk, text, flags=re.IGNORECASE):
            #print(row)
            return False
    return True

def generate_w3c_annotation():
    return {
        "@context": "http://www.w3.org/ns/anno.jsonld",
        "type": "Annotation",
        "generator": {
            "id": "http://github.com/marijnkoolen/impact-of-reading",
            "type": "Software",
            "homepage": "http://github.com/marijnkoolen/impact-of-reading",
        }
    }

def make_w3c_impact_target(doc_id, doc_type, text_position):
    return [{
        "source": doc_id,
        "type": ["Text", doc_type],
        "selector": [
            {
                "type": "TextPositionSelector",
                "start": text_position["start"],
                "end": text_position["end"],
            },
            {
                "type": "TextPositionSelector",
                "text": text_position["text"],
                "prefix": text_position["prefix"],
                "suffix": text_position["suffix"],
            },
        ]
    }]

def make_match_w3c_annotation(doc_id, doc_type, impact_match):
    annotation = generate_w3c_annotation()
    annotation["body"] = {
        "type": "classification",
        "id": "impact-term-id",
        "purpose": "classifying",
        "value": impact_match["impact_term"]
    }
    annotation["target"] = []
    for text_position in impact_match["TextPosition"]:
    	annotation["target"] += make_w3c_impact_target(doc_id, doc_type, text_position)
    return annotation

def w3c_annotate_impact(doc_id, doc_type, doc_text):
    impact = annotate_impact(doc_text)
    return [make_match_w3c_annotation(doc_id, doc_type, impact_match) for impact_match in impact["impact_matches"]]

def set_prefix_offset(text, start_offset):
    prefix_offset = start_offset - CONTEXT_LENGTH if start_offset >= CONTEXT_LENGTH else 0
    if prefix_offset == 0 or text[prefix_offset] == " ":
        return prefix_offset
    while prefix_offset > 0 and text[prefix_offset-1] != " ":
        prefix_offset -= 1
    return prefix_offset

def set_suffix_end_offset(text, end_offset):
    suffix_end = end_offset + CONTEXT_LENGTH
    if suffix_end >= len(text) or text[suffix_end] == " ":
        return suffix_end
    while suffix_end < len(text) - 1 and text[suffix_end] != " ":
        suffix_end += 1
    return suffix_end

def make_text_position_selector(match_part, match_start_offset, text):
    match_end_offset = match_start_offset + len(match_part)
    prefix_start_offset = set_prefix_offset(text, match_start_offset)
    suffix_end_offset = set_suffix_end_offset(text, match_end_offset)
    return [{
        "start": match_start_offset,
        "end": match_end_offset,
        "text": match_part,
        "prefix": text[prefix_start_offset:match_start_offset],
        "suffix": text[match_end_offset:suffix_end_offset],
    }]

def extract_match(match, annotated):
    text_positions = []
    for match_part in match:
        if len(match_part) == 0:
            continue
        match_start_offset = annotated["sentence"].index(match_part)
        text_positions += make_text_position_selector(match_part, match_start_offset, annotated["sentence"])
        try:
            match_part = re.sub(r"([\(\)\[\]\{\}\*\.\?])", r"\\\1", match_part)
            annotated["annotated_sentence"] = re.sub(match_part, "<match_part-{i}>".format(i=len(annotated["impact_matches"]) + 1), annotated["annotated_sentence"])
        except:
            print(match_part)
            raise
    return text_positions

def make_regexp_impact_term(impact_group, impact_term):
    if impact_term == "*zucht*":
        impact_term = impact_term.replace("*", "\*")
    if "adjective" in impact_group and impact_term[-1] == "*":
        impact_term = "(" + impact_term.replace("*", "(e|er|st)?") + ")"
    if "noun" in impact_group and impact_term[-1] == "*":
        impact_term = "(" + impact_term.replace("*", "(es|en|s)?") + ")"
    return r"\b%s\b" % impact_term

def lookup_term(impact_group, impact_term, annotated):
    search_string = make_regexp_impact_term(impact_group, impact_term)
    matches = re.findall(search_string, annotated["sentence"], flags=re.IGNORECASE)
    for index, match in enumerate(matches):
        if type(match) == str:
            text_position = extract_match([match], annotated)
        elif type(match) == tuple:
            text_position = extract_match(match, annotated)
        annotated["impact_matches"] += [{"impact_term": impact_term, "impact_group": impact_group, "TextPosition": text_position}]

def make_discontinuous_phrase_pattern(pattern):
    return r"(.*?)\b%s\b(.*)" % pattern.replace(") (", ")(.*? )(")

def make_continuous_phrase_pattern(pattern):
    return r"(.*?)\b(%s)\b(.*)" % pattern

def make_phrase_regex_pattern(impact_phrase, impact_group):
    if is_discontinuous_phrase_group(impact_group):
        return make_discontinuous_phrase_pattern(impact_phrase)
    else:
        return make_continuous_phrase_pattern(impact_phrase)

def make_match_part(offset, match_part):
    return {
        "exact": match_part,
        "start": offset,
        "end": offset + len(match_part)
    }

def determine_discontinuous_match_offsets(match_parts, text):
    offset = 0
    text_positions = []
    for index, match_part in enumerate(match_parts):
        if index % 2 == 1:
            text_position = make_text_position_selector(match_part, offset, text)
            text_positions.append(text_position)
        offset += len(match_part)
    return text_positions

def determine_continuous_match_offsets(match, text):
    offset = len(match)
    return [make_text_position_selector(match, offset, text)]

def determine_phrase_match_offsets(match_parts, impact_group, text):
    if is_discontinuous_phrase_group(impact_group):
        return determine_discontinuous_match_offsets(match_parts, text)
    else:
        return determine_continuous_match_offsets(match_parts[0], text)

def lookup_phrase(impact_group, impact_phrase, annotated):
    pattern = make_phrase_regex_pattern(impact_phrase, impact_group)
    matches = re.findall(pattern, annotated["sentence"], flags=re.IGNORECASE)
    for match in matches:
        text_position = determine_phrase_match_offsets(match, impact_group, annotated["sentence"])
        annotated["impact_matches"] += [{"impact_term": impact_phrase, "impact_group": impact_group, "TextPosition": text_position}]

def is_discontinuous_phrase_group(impact_group):
    return "discontinuous" in impact_group

def is_phrase_group(impact_group):
    return "_phrase" in impact_group

def annotate_impact(sentence):
    annotated = {
        "sentence": sentence,
        "annotated_sentence": sentence,
        "impact_matches": [],
    }
    for impact_group in impact_groups:
        # check if context is present

        # iterate over impact terms
        for impact_term in impact_groups[impact_group]["terms"]:
            if is_phrase_group(impact_group):
                lookup_phrase(impact_group, impact_term, annotated)
            else:
                lookup_term(impact_group, impact_term, annotated)
    return annotated

if __name__ == "__main__":
    test_sent = "De schrijfstijl is meeslepend en doet me denken aan iets anders"
    matches = annotate_impact(test_sent)
    print(json.dumps(matches, indent=4))


