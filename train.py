#!/usr/bin/env python
# coding: utf-8
"""Using the parser to recognise your own semantics

spaCy's parser component can be trained to predict any type of tree
structure over your input text. You can also predict trees over whole documents
or chat logs, with connections between the sentence-roots used to annotate
discourse structure. In this example, we'll build a message parser for a common
"chat intent": finding local businesses. Our message semantics will have the
following types of relations: ROOT, PLACE, QUALITY, ATTRIBUTE, TIME, LOCATION.

"show me the best hotel in berlin"
('show', 'ROOT', 'show')
('best', 'QUALITY', 'hotel') --> hotel with QUALITY best
('hotel', 'PLACE', 'show') --> show PLACE hotel
('berlin', 'LOCATION', 'hotel') --> hotel with LOCATION berlin

Compatible with: spaCy v2.0.0+
"""
from __future__ import unicode_literals, print_function

import plac
import random
from pathlib import Path
import spacy
from spacy.util import minibatch, compounding


# training data: texts, heads and dependency labels
# for no relation, we simply chose an arbitrary dependency label, e.g. '-'
TRAIN_DATA = [
    (
        #0  1
        "hi there",
        {
            "heads": [0, 0],  # index of token head
            "deps": ["ROOT", "-"],
        },
    ),
    (
        #0   1
        "hey you",
        {
            "heads": [0, 0],
            "deps": ["ROOT", "TARGET"],
        },
    ),
    (
        #0     1
        "hello bot",
        {
            "heads": [0, 0],
            "deps": ["ROOT", "TARGET"],
        },
    ),
    (
        #0    1
        "good morning",
        {
            "heads": [1, 1],
            "deps": ["QUALITY", "ROOT"],
        },
    ),
    (
        #0
        "hi",
        {
            "heads": [0],
            "deps": ["ROOT"],
        },
    ),
    (
        #0   1   2
        # are -> is -> Situacion actual, estado, sentimientos, etc
        "how are you",
        {
            "heads": [0, 2, 0],
            "deps": ["ROOT", "STATE", "TARGET"],
        },
    ),
    (
        #0   1   2   3
        "how are you feeling",
        {
            "heads": [0, 2, 0, 2],
            "deps": ["ROOT", "STATE", "TARGET", "STATE"],
        },
    ),
    (
        #0   1   2   3
        "how are you doing",
        {
            "heads": [0, 2, 0, 2],
            "deps": ["ROOT", "STATE", "TARGET", "STATE"],
        },
    ),
    (
        #0   1   2
        "how you doing",
        {
            "heads": [0, 2, 0],
            "deps": ["ROOT", "STATE", "TARGET"],
        },
    ),
    (
        #0    1    2   3  4
        "what will you do tomorrow",
        {
            "heads": [0, 2, 0, 0, 3],
            "deps": ["ROOT", "-", "TARGET", "ACTION", "TIME"],
        },
    ),
    (
        #0    1   2   3
        "what are you doing",
        {
            "heads": [0, 2, 0, 2],
            "deps": ["ROOT", "STATE", "TARGET", "ACTION"],
        },
    ),
    (
        #0    1   2   3     4  5    6
        "what are you doing in this moment",
        {
            "heads": [0, 2, 0, 2, 3, 0, 3],
            "deps": ["ROOT", "STATE", "TARGET", "ACTION", "-", "-", "TIME"],
        },
    ),
    (
        #0    1   2   3  4
        "what did you do yesterday",
        {
            "heads": [0, 2, 2, 0, 3],
            "deps": ["ROOT", "-", "TARGET", "ACTION", "TIME"],
        }
    )
    # (
    #     #0    1 2    3    4     5
    #     "find a cafe with great wifi",
    #     {
    #         "heads": [0, 2, 0, 5, 5, 2],  # index of token head
    #         "deps": ["ROOT", "-", "PLACE", "-", "QUALITY", "ATTRIBUTE"],
    #     },
    # ),
    # (
    #     #0    1 2     3    4   5
    #     "find a hotel near the beach",
    #     {
    #         "heads": [0, 2, 0, 5, 5, 2],
    #         "deps": ["ROOT", "-", "PLACE", "QUALITY", "-", "ATTRIBUTE"],
    #     },
    # ),
    # (
    #     "find me the closest gym that's open late",
    #     {
    #         "heads": [0, 0, 4, 4, 0, 6, 4, 6, 6],
    #         "deps": [
    #             "ROOT",
    #             "-",
    #             "-",
    #             "QUALITY",
    #             "PLACE",
    #             "-",
    #             "-",
    #             "ATTRIBUTE",
    #             "TIME",
    #         ],
    #     },
    # ),
    # (
    #     "show me the cheapest store that sells flowers",
    #     {
    #         "heads": [0, 0, 4, 4, 0, 4, 4, 4],  # attach "flowers" to store!
    #         "deps": ["ROOT", "-", "-", "QUALITY", "PLACE", "-", "-", "PRODUCT"],
    #     },
    # ),
    # (
    #     "find a nice restaurant in london",
    #     {
    #         "heads": [0, 3, 3, 0, 3, 3],
    #         "deps": ["ROOT", "-", "QUALITY", "PLACE", "-", "LOCATION"],
    #     },
    # ),
    # (
    #     "show me the coolest hostel in berlin",
    #     {
    #         "heads": [0, 0, 4, 4, 0, 4, 4],
    #         "deps": ["ROOT", "-", "-", "QUALITY", "PLACE", "-", "LOCATION"],
    #     },
    # ),
    # (
    #     "find a good italian restaurant near work",
    #     {
    #         "heads": [0, 4, 4, 4, 0, 4, 5],
    #         "deps": [
    #             "ROOT",
    #             "-",
    #             "QUALITY",
    #             "ATTRIBUTE",
    #             "PLACE",
    #             "ATTRIBUTE",
    #             "LOCATION",
    #         ],
    #     },
    # ),
]


@plac.annotations(
    model=("Model name. Defaults to blank 'en' model.", "option", "m", str),
    output_dir=("Optional output directory", "option", "o", Path),
    n_iter=("Number of training iterations", "option", "n", int),
)
def main(model=None, output_dir=None, n_iter=15):
    """Load the model, set up the pipeline and train the parser."""
    if model is not None:
        nlp = spacy.load(model)  # load existing spaCy model
        print("Loaded model '%s'" % model)
    else:
        nlp = spacy.blank("en")  # create blank Language class
        print("Created blank 'en' model")

    # We'll use the built-in dependency parser class, but we want to create a
    # fresh instance – just in case.
    if "parser" in nlp.pipe_names:
        nlp.remove_pipe("parser")
    parser = nlp.create_pipe("parser")
    nlp.add_pipe(parser, first=True)

    for text, annotations in TRAIN_DATA:
        for dep in annotations.get("deps", []):
            parser.add_label(dep)

    pipe_exceptions = ["parser", "trf_wordpiecer", "trf_tok2vec"]
    other_pipes = [pipe for pipe in nlp.pipe_names if pipe not in pipe_exceptions]
    with nlp.disable_pipes(*other_pipes):  # only train parser
        optimizer = nlp.begin_training()
        for itn in range(n_iter):
            random.shuffle(TRAIN_DATA)
            losses = {}
            # batch up the examples using spaCy's minibatch
            batches = minibatch(TRAIN_DATA, size=compounding(4.0, 32.0, 1.001))
            for batch in batches:
                texts, annotations = zip(*batch)
                nlp.update(texts, annotations, sgd=optimizer, losses=losses)
            # print("Losses", losses)

    # test the trained model
    test_model(nlp)

    # save model to output directory
    if output_dir is not None:
        output_dir = Path(output_dir)
        if not output_dir.exists():
            output_dir.mkdir()
        nlp.to_disk(output_dir)
        print("Saved model to", output_dir)

        # test the saved model
        print("Loading from", output_dir)
        nlp2 = spacy.load(output_dir)
        test_model(nlp2)


def test_model(nlp):
    texts = [
        "hello bot",
        "hello there",
        "hi good morning",
        "hey bot",
        "Hello",
        "HI THERE",

        "Toaster",
        "Water bottle",
        "Buy things",

        "How are you doing bot",
        "How do you do",
        "How do you feel",

        "What will you do tomorrow",
        "What are you doing in this moment",
        "What did you do yesterday",

        # "how is the weather",
        # "how did the cat get there",
        # "how can I find the restroom",

        "hi my name is Elias"

        


        
        # "find a hotel with good wifi",
        # "find me the cheapest gym near work",
        # "show me the best hotel in berlin",
    ]
    greetings = ["hi", "hello", "hey", "morning", "afternoon", "yo"]
    greeting_responses = [
        "Hi!",
        "Hello friendly human.",
        "Hi there!",
        "Hey!",
    ]
    welcome_responses = [
        "Hi there! I'm a bot and you can say hi to me.",
        "Hello! I'm a greeting bot.",
        "Welcome, feel free to say hi to me anytime.",
        "Hey human! I'm a bot, but you can say hi to me and I'll do my best to try and answer.",
    ]
    questions = ["how", "what"]
    targets_self = ["bot", "you", "chatbot"]
    self_state_responses = [
        "I'm doing fine thank you.",
        "Thanks for asking, I'm doing alright.",
        "Right now I'm feeling great! Just a little sleepy",
    ]
    doing_responses_past = ["I was on the bed all day.",]
    doing_responses_present = ["I don´t know",]
    doing_responses_future = [ "I´ll see that in a few hours",]
    time_past = ["yesterday"]
    time_present = ["moment"]
    time_future = ["tomorrow"]

    
    
    docs = nlp.pipe(texts)
    for doc in docs:
        print(doc.text)
        print([(t.text, t.dep_, t.head.text) for t in doc if t.dep_ != "-"])
        for ent in doc.ents:
            print(ent.text, ent.start_char, ent.end_char, ent.label_)

        # Dependency label dictionary
        label_dict = {t.dep_ : t for t in doc}
        print(f"label_dict: {label_dict}")

        responses = []

        # Revisar si el ROOT es un saludo conocido
        if label_dict["ROOT"].text.lower() in greetings:
            # Responder con un saludo aleatorio
            responses += [random.choice(greeting_responses)]
        elif label_dict["ROOT"].text.lower() in questions:
            # Es una pregunta
            # Responder si preguntan cómo estamos
            if "STATE" in label_dict and "ACTION" not in label_dict and label_dict["TARGET"].text.lower() in targets_self:
                responses += [random.choice(self_state_responses)]
            elif "ACTION" in label_dict and label_dict["TARGET"].text.lower() in targets_self:
                if "TIME" in label_dict and label_dict["TIME"].text.lower() in time_past:
                    responses += [random.choice(doing_responses_past)]
                elif "TIME" in label_dict and label_dict["TIME"].text.lower() in time_present:
                    responses += [random.choice(doing_responses_present)]
                elif "TIME" in label_dict and label_dict["TIME"].text.lower() in time_future:
                    responses += [random.choice(doing_responses_future)]
                else:
                    responses += ["I can't response that."]
            else:
                responses += ["I'm sorry, I'm not sure how to answer that."]
        else:
            # Responder con un mensaje de bienvenida aleatorio
            responses += [random.choice(welcome_responses)]

       

        print("Response:")
        print(responses)

        print("\n")
        print("-" * 20)
        print("\n")


if __name__ == "__main__":
    plac.call(main)

    # Expected output:
    # find a hotel with good wifi
    # [
    #   ('find', 'ROOT', 'find'),
    #   ('hotel', 'PLACE', 'find'),
    #   ('good', 'QUALITY', 'wifi'),
    #   ('wifi', 'ATTRIBUTE', 'hotel')
    # ]
    # find me the cheapest gym near work
    # [
    #   ('find', 'ROOT', 'find'),
    #   ('cheapest', 'QUALITY', 'gym'),
    #   ('gym', 'PLACE', 'find'),
    #   ('near', 'ATTRIBUTE', 'gym'),
    #   ('work', 'LOCATION', 'near')
    # ]
    # show me the best hotel in berlin
    # [
    #   ('show', 'ROOT', 'show'),
    #   ('best', 'QUALITY', 'hotel'),
    #   ('hotel', 'PLACE', 'show'),
    #   ('berlin', 'LOCATION', 'hotel')
    # ]