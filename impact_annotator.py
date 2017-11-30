import json
import re
from Model.impact_model import impact_groups, impact_contexts

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

def extract_match(match, annotated):
    text_position = []
    for match_part in match:
        text_position += [{
            "start": annotated["sentence"].index(match_part),
            "end": annotated["sentence"].index(match_part) + len(match_part),
            "text": match_part,
        }]
        annotated["annotated_sentence"] = re.sub(match_part, "<match_part-{i}>".format(i=len(annotated["impact_matches"]) + 1), annotated["annotated_sentence"])
    return text_position

def lookup_term(impact_group, impact_term, annotated):
    impact_term = impact_term.replace("*", "\*")
    search_string = r"\b%s\b" % impact_term
    matches = re.findall(search_string, annotated["sentence"], flags=re.IGNORECASE)
    for index, match in enumerate(matches):
        if type(match) == str:
            text_position = extract_match([match], annotated)
        elif type(match) == tuple:
            text_position = extract_match(match, annotated)
        annotated["impact_matches"] += [{"impact_term": impact_term, "impact_group": impact_group, "TextPosition": text_position}]

def impact_annotator(sentence):
    annotated = {
        "sentence": sentence,
        "annotated_sentence": sentence,
        "impact_matches": [],
    }
    for impact_group in impact_groups:
        # check if context is present

        # iterate over impact terms
        for impact_term in impact_groups[impact_group]["terms"]:
            lookup_term(impact_group, impact_term, annotated)
    return annotated

if __name__ == "__main__":
    test_sent = "De schrijfstijl is meeslepend en doet me denken aan iets anders"
    matches = impact_annotator(test_sent)
    print(json.dumps(matches, indent=4))


