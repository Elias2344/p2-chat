import spacy
import random

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
questions = ["how"]
targets_self = ["bot", "you", "chatbot"]
self_state_responses = [
    "I'm doing fine thank you.",
    "Thanks for asking, I'm doing alright.",
    "Right now I'm feeling great! Just a little sleepy.",
]
doing_responses_past = ["I was on the bed all day.",]
doing_responses_present = ["I don´t know",]
doing_responses_future = [ "I´ll see that in a few hours",]
time_past = ["yesterday"]
time_present = ["moment"]
time_future = ["tomorrow"]

class AI():


    def __init__(self):
        self.nlp = spacy.load('model')

    def message(self, msg):
        if not msg:
            return None

        doc = self.nlp(msg)

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

        return ' '.join(responses)


