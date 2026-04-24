STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above",
    "below", "between", "out", "off", "over", "under", "again",
    "further", "then", "once", "here", "there", "when", "where", "why",
    "how", "all", "both", "each", "few", "more", "most", "other",
    "some", "such", "no", "nor", "not", "only", "own", "same", "so",
    "than", "too", "very", "just", "don", "now", "and", "but", "or",
    "because", "if", "while", "that", "this", "it", "its", "which",
    "what", "who", "whom", "these", "those", "am", "about", "up",
    "also", "like", "many", "much", "well", "even", "back", "made",
    "make", "take", "come", "know", "see", "look", "find", "give",
    "tell", "say", "get", "got", "goes", "went", "going", "using",
    "called", "based", "given", "different", "another", "first",
    "second", "third", "last", "next", "new", "old", "long", "short",
    "one", "two", "three", "four", "five", "six", "etc", "per",
    "every", "still", "thing", "things", "must", "often", "part",
    "really", "something", "already", "always", "without", "within",
}

QUESTION_TYPES = [
    {
        "intent": "explain",
        "templates": [
            "The document states: '{topic}'. Can you explain the underlying principles behind this in your own words?",
            "Regarding the excerpt, '{topic}', what exactly does this mean and why is it significant?",
            "Please elaborate on this statement from the material: '{topic}'.",
        ]
    },
    {
        "intent": "analyze",
        "templates": [
            "Looking at the concept that '{topic}', what are the key factors involved, and how do they interact?",
            "Analyze the following point from the text: '{topic}'. What are its causes, effects, or implications?",
            "What deeper insights can you draw from the statement: '{topic}'? Discuss the reasoning behind it.",
        ]
    },
    {
        "intent": "apply",
        "templates": [
            "How would you apply the principle that '{topic}' in a practical, real-world scenario?",
            "If you had to solve a problem based on the fact that '{topic}', how would you approach it?",
            "Consider the statement: '{topic}'. What practical implications does this have?",
        ]
    },
    {
        "intent": "compare",
        "templates": [
            "The text mentions: '{topic}'. How does this relate to or contrast with other concepts you've read in the document?",
            "In the context of the statement '{topic}', what alternative perspectives or trade-offs could be considered?",
        ]
    },
    {
        "intent": "evaluate",
        "templates": [
            "Critically evaluate the following point from the text: '{topic}'. What are its strengths and potential limitations?",
            "Why is it considered important that '{topic}'? What would change if this were not the case?",
            "Assess the validity and role of this claim: '{topic}'. Do you agree with the approach described?",
        ]
    },
    {
        "intent": "synthesize",
        "templates": [
            "Summarize the key ideas surrounding the statement '{topic}' and explain how they connect to the broader themes.",
            "Pull together the various points related to '{topic}'. What is the overall message or conclusion?",
            "How does the concept that '{topic}' fit into the bigger picture presented in the document? Connect the dots.",
        ]
    },
]
