from backend.nlp.nlp_main import extract_spacy

def test_spacy_nlp():
    user_text = "I have 2 bags and need wheelchair assistance"
    
    result = extract_spacy(user_text)
    data = result
    
    print(data)