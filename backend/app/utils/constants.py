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
            "Based on the document, explain in your own words: {topic}. Why is this significant?",
            "The document discusses {topic}. Can you explain the underlying concepts and their importance?",
            "Walk me through your understanding of {topic} as presented in the material.",
        ]
    },
    {
        "intent": "analyze",
        "templates": [
            "Looking at {topic}, what are the key factors or components involved, and how do they interact?",
            "Analyze {topic} from the document. What are its causes, effects, or implications?",
            "What deeper insights can you draw about {topic}? Discuss the reasoning behind it.",
        ]
    },
    {
        "intent": "apply",
        "templates": [
            "How would you apply the concept of {topic} in a real-world scenario? Give a practical example.",
            "If you had to use {topic} to solve a problem, how would you approach it?",
            "What practical implications does {topic} have? How might it be used or implemented?",
        ]
    },
    {
        "intent": "compare",
        "templates": [
            "How does {topic} relate to or differ from other concepts discussed in the document?",
            "Compare the different aspects of {topic}. What are the trade-offs or complementary elements?",
            "In the context of {topic}, what are the main arguments or perspectives presented?",
        ]
    },
    {
        "intent": "evaluate",
        "templates": [
            "Critically evaluate {topic}. What are its strengths and potential limitations?",
            "Why is {topic} considered important in this context? What would change without it?",
            "Assess the role of {topic}. Do you think the approach described is effective? Why?",
        ]
    },
    {
        "intent": "synthesize",
        "templates": [
            "Summarize the key ideas around {topic} and explain how they connect to the broader themes in the document.",
            "Pull together the various points about {topic}. What is the overall message or conclusion?",
            "How does {topic} fit into the bigger picture presented in the document? Connect the dots.",
        ]
    },
]
