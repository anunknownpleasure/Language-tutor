"""
Run once to create tables and seed vocabulary + lesson patterns.
Usage: python seed.py

WARNING: This drops and recreates all tables — for development only.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from database import Base, engine, AsyncSessionLocal
from models import User, Vocabulary, LessonPattern


# ── Lesson patterns ────────────────────────────────────────────────────────
# One row per lesson. Holds the MT sentence pattern + explanation + tip.
# (level, lesson_number, pattern_fr, pattern_en, explanation, tip)

LESSON_PATTERNS = [
    # ── A1 ──────────────────────────────────────────────────────────────────
    (
        "A1", 1,
        "Bonjour ! Je m'appelle [name].",
        "Hello! My name is [name].",
        "'Je m'appelle' literally means 'I call myself' — it comes from the verb 'appeler' (to call). "
        "The 'm'' is a reflexive pronoun meaning 'myself'. Add your name at the end and you can "
        "introduce yourself anywhere in France.",
        "Pronunciation: 'je m'appelle' = 'zhuh mah-PEL'. The 'j' sounds like the 's' in 'measure'.",
    ),
    (
        "A1", 2,
        "Je voudrais [thing], s'il vous plaît.",
        "I would like [thing], please.",
        "'Voudrais' is the polite/conditional form of 'vouloir' (to want). It's the equivalent of "
        "saying 'I would like' rather than 'I want' — instantly more polite. This single pattern "
        "works in any café, shop, hotel, or ticket office in France.",
        "Pronunciation: 'je voudrais' = 'zhuh voo-DREH'. The '-ais' ending sounds like 'eh'.",
    ),
    (
        "A1", 3,
        "C'est [adjective/noun]. / Ce n'est pas [adjective/noun].",
        "It is [adjective/noun]. / It is not [adjective/noun].",
        "'C'est' is a contraction of 'ce est' — meaning 'it is' or 'that is'. It's universal: "
        "you can describe food, places, people, situations. The negative flips to 'ce n'est pas' "
        "(it is not). Many French adjectives look like English ones — 'excellent', 'magnifique', "
        "'parfait' — you already know more than you think.",
        "Pronunciation: 'c'est' = 'say'. 'Ce n'est pas' = 'suh neh PAH'.",
    ),
    (
        "A1", 4,
        "Je vais à [place]. / Je voudrais aller à [place].",
        "I am going to [place]. / I would like to go to [place].",
        "'Vais' is the first-person form of 'aller' (to go) — one of the most useful verbs in French. "
        "Combine it with any destination. For a polite request, use 'je voudrais aller à' — "
        "the same 'voudrais' from Lesson 2, now paired with 'aller' (to go).",
        "Note: 'à la' before feminine nouns (à la gare), 'au' before masculine (au marché = à + le).",
    ),
    (
        "A1", 5,
        "Où est [place] ? / C'est à gauche / à droite / tout droit.",
        "Where is [place]? / It's to the left / to the right / straight ahead.",
        "'Où' means 'where' — just two letters and it unlocks every direction question. "
        "The answer pattern uses 'c'est' from Lesson 3, so you're already halfway there. "
        "'Gauche' and 'droite' are worth memorising — you'll use them every day in France.",
        "Memory trick: 'gauche' sounds a bit like 'gauche' in English (meaning clumsy, left-handed). "
        "And 'droite' shares roots with 'right' (correct, righteous).",
    ),
    (
        "A1", 6,
        "J'aime [thing]. / Je n'aime pas [thing].",
        "I like [thing]. / I don't like [thing].",
        "'J'aime' comes from the verb 'aimer' (to like/love). The negation wraps around the verb: "
        "'ne' before and 'pas' after, making 'je n'aime pas'. In casual speech, French people often "
        "drop the 'ne': 'j'aime pas' — you'll hear this constantly. 'Aimer' works with nouns AND "
        "infinitive verbs: 'j'aime manger' (I like eating).",
        "Pronunciation: 'j'aime' = 'ZHEM'. 'Je n'aime pas' = 'zhuh nem PAH'.",
    ),
    (
        "A1", 7,
        "Je peux [verb]. / Pouvez-vous [verb] ?",
        "I can [verb]. / Can you [verb]?",
        "'Peux' is the first-person form of 'pouvoir' (to be able to / can). "
        "'Pouvez-vous' is the polite/formal 'can you?' — you invert the verb and subject. "
        "This pattern unlocks asking for help, requesting repetition, and checking your own abilities. "
        "It pairs with any infinitive verb.",
        "Pronunciation: 'je peux' = 'zhuh PUH'. 'Pouvez-vous' = 'poo-VAY voo'.",
    ),
    (
        "A1", 8,
        "J'ai [noun]. / Il y a [noun].",
        "I have [noun]. / There is/are [noun].",
        "'J'ai' is the first-person form of 'avoir' (to have) — one of the two most important verbs "
        "in French. 'Il y a' means 'there is' or 'there are' — three words that work for "
        "everything: 'il y a un problème' (there is a problem), 'il y a deux personnes' (there are "
        "two people). Many English expressions that use 'to be' use 'avoir' in French: "
        "'j'ai faim' = I am hungry (literally: I have hunger).",
        "Pronunciation: 'j'ai' = 'ZHAY'. 'Il y a' = 'eel ee AH'.",
    ),
    (
        "A1", 9,
        "À quelle heure [verb] ? / À [number] heures.",
        "At what time does [thing] [verb]? / At [number] o'clock.",
        "'À quelle heure' literally means 'at what hour' — a three-word phrase that opens every "
        "time question. The answer always starts with 'à' (at) followed by the number and 'heures' "
        "(hours/o'clock). This pattern is essential for trains, museums, restaurants — anything "
        "with an opening or departure time.",
        "Pronunciation: 'à quelle heure' = 'ah kel URR'. 'Heures' = 'URR' (the 'h' is silent).",
    ),
    (
        "A1", 10,
        "Qu'est-ce que c'est ? / C'est un/une [noun].",
        "What is it? / It is a [noun].",
        "'Qu'est-ce que c'est' is literally 'what is it that it is' — French is wonderfully "
        "logical once you see the pieces. In practice it just means 'what is this/that?' "
        "The answer uses 'c'est' from Lesson 3, so you already know half the answer. "
        "'Un' is used before masculine nouns, 'une' before feminine ones.",
        "Pronunciation: 'qu'est-ce que c'est' = 'kess kuh SAY'. Often shortened in speech to 'c'est quoi ça?'",
    ),

    # ── A2 ──────────────────────────────────────────────────────────────────
    (
        "A2", 1,
        "Je voudrais commander... / Je prends [dish].",
        "I would like to order... / I'll have [dish].",
        "In restaurants, 'je voudrais commander' opens your order politely. "
        "'Je prends' (I'll take/have) is more casual and very natural. Both are essential "
        "for navigating a French menu confidently.",
        None,
    ),
    (
        "A2", 2,
        "Pour aller à [place], vous [direction].",
        "To get to [place], you [direction].",
        "This is the giving-directions pattern. 'Pour aller à' (to get to) sets up the destination, "
        "then you describe the route. Combine with verbs like 'tournez' (turn), 'continuez' "
        "(continue), 'prenez' (take).",
        None,
    ),
    (
        "A2", 3,
        "Je cherche [item]. / Combien coûte [item] ?",
        "I am looking for [item]. / How much does [item] cost?",
        "'Je cherche' (I am looking for) is your shopping opener. "
        "'Combien coûte' (how much does it cost) closes the deal. "
        "Together they handle 80% of any shopping interaction.",
        None,
    ),
    (
        "A2", 4,
        "J'ai mal à [body part]. / Je ne me sens pas bien.",
        "I have a pain in [body part]. / I don't feel well.",
        "French uses 'avoir mal à' (to have pain in) rather than 'my X hurts'. "
        "'Je ne me sens pas bien' is the all-purpose 'I don't feel well' — essential for "
        "pharmacies and doctors.",
        None,
    ),
    (
        "A2", 5,
        "Dans mon/ma [room], il y a [thing]. / J'habite à [place].",
        "In my [room], there is [thing]. / I live in [place].",
        "'Dans' means 'in/inside'. Combined with 'il y a' from A1 Lesson 8, you can describe "
        "any living space. 'J'habite' (I live/I reside) comes from 'habiter' — a regular -er verb.",
        None,
    ),
    (
        "A2", 6,
        "Je travaille comme [job]. / Je commence à [time].",
        "I work as a [job]. / I start at [time].",
        "'Travailler' (to work) is a regular -er verb. 'Comme' here means 'as' in the sense "
        "of occupation. 'Je commence à' (I start at) pairs naturally with the time pattern "
        "from A1 Lesson 9.",
        None,
    ),
    (
        "A2", 7,
        "J'adore [activity]. / Je fais [activity] [frequency].",
        "I love [activity]. / I do [activity] [how often].",
        "'J'adore' is stronger than 'j'aime' — it means 'I love/adore'. "
        "'Je fais' (I do/I play) comes from 'faire', one of the most versatile verbs in French. "
        "Used for sports, hobbies, activities: 'je fais du sport', 'je fais de la musique'.",
        None,
    ),
    (
        "A2", 8,
        "Je me sens [emotion]. / Ça me rend [emotion].",
        "I feel [emotion]. / It makes me [emotion].",
        "'Se sentir' (to feel) is a reflexive verb. 'Ça me rend' (that makes me) is incredibly "
        "expressive — 'ça me rend heureux' (that makes me happy), 'ça me rend triste' (that makes "
        "me sad). Two patterns that cover the full emotional range.",
        None,
    ),
    (
        "A2", 9,
        "Je pars à [destination] pour [duration]. / J'ai besoin de [thing].",
        "I'm leaving for [destination] for [duration]. / I need [thing].",
        "'Partir' (to leave/depart) is an irregular verb — 'je pars' is essential for travel. "
        "'J'ai besoin de' (I need) literally means 'I have need of' — another case where French "
        "uses 'avoir' where English uses 'to be'.",
        None,
    ),
    (
        "A2", 10,
        "D'habitude, je [activity] à [time].",
        "Usually, I [activity] at [time].",
        "'D'habitude' (usually/normally) sets up a routine. It's an adverb of frequency that "
        "makes any sentence sound natural and fluent. Pair it with reflexive verbs like "
        "'se réveiller', 'se doucher', 'se coucher' to describe your whole day.",
        None,
    ),
]


# ── Vocabulary ─────────────────────────────────────────────────────────────
# (word_fr, word_en, example_sentence_fr, level, lesson_number)
# A1 example sentences all use the lesson's MT pattern.

VOCABULARY = [
    # ── A1 ──────────────────────────────────────────────────────────────────

    # Lesson 1 — Greetings (Pattern: "Bonjour ! Je m'appelle [name].")
    ("bonjour", "hello / good day", "Bonjour ! Je m'appelle Sophie.", "A1", 1),
    ("bonsoir", "good evening", "Bonsoir ! Je m'appelle Marie.", "A1", 1),
    ("je m'appelle", "my name is", "Bonjour, je m'appelle Pierre !", "A1", 1),
    ("enchanté", "pleased to meet you", "Bonjour, je m'appelle Claire — enchantée !", "A1", 1),
    ("au revoir", "goodbye", "Au revoir ! À bientôt !", "A1", 1),
    ("s'il vous plaît", "please (formal)", "Bonjour, s'il vous plaît — où est la gare ?", "A1", 1),
    ("merci", "thank you", "Merci beaucoup, au revoir !", "A1", 1),

    # Lesson 2 — Ordering (Pattern: "Je voudrais [thing], s'il vous plaît.")
    ("un café", "a coffee", "Je voudrais un café, s'il vous plaît.", "A1", 2),
    ("un thé", "a tea", "Je voudrais un thé, s'il vous plaît.", "A1", 2),
    ("de l'eau", "some water", "Je voudrais de l'eau, s'il vous plaît.", "A1", 2),
    ("un billet", "a ticket", "Je voudrais un billet pour Paris, s'il vous plaît.", "A1", 2),
    ("l'addition", "the bill", "Je voudrais l'addition, s'il vous plaît.", "A1", 2),
    ("un croissant", "a croissant", "Je voudrais un croissant, s'il vous plaît.", "A1", 2),
    ("une baguette", "a baguette", "Je voudrais une baguette, s'il vous plaît.", "A1", 2),

    # Lesson 3 — Describing (Pattern: "C'est [adj]. / Ce n'est pas [adj].")
    ("bon", "good / tasty", "C'est très bon, merci !", "A1", 3),
    ("mauvais", "bad", "Ce n'est pas mauvais du tout !", "A1", 3),
    ("grand", "big / tall", "C'est grand ici !", "A1", 3),
    ("petit", "small", "C'est petit mais confortable.", "A1", 3),
    ("beau", "beautiful", "C'est beau, Paris !", "A1", 3),
    ("cher", "expensive", "Ce n'est pas cher !", "A1", 3),
    ("loin", "far", "Ce n'est pas loin d'ici.", "A1", 3),

    # Lesson 4 — Going places (Pattern: "Je vais à [place]. / Je voudrais aller à [place].")
    ("la gare", "the train station", "Je voudrais aller à la gare, s'il vous plaît.", "A1", 4),
    ("l'hôtel", "the hotel", "Je vais à l'hôtel ce soir.", "A1", 4),
    ("le restaurant", "the restaurant", "Je voudrais aller à un bon restaurant.", "A1", 4),
    ("la banque", "the bank", "Je vais à la banque ce matin.", "A1", 4),
    ("le marché", "the market", "Je voudrais aller au marché.", "A1", 4),
    ("le musée", "the museum", "Je vais au musée demain.", "A1", 4),
    ("l'aéroport", "the airport", "Je voudrais aller à l'aéroport, s'il vous plaît.", "A1", 4),

    # Lesson 5 — Directions (Pattern: "Où est [place] ? / C'est à gauche / droite / tout droit.")
    ("à gauche", "to the left", "La boulangerie ? C'est à gauche.", "A1", 5),
    ("à droite", "to the right", "La gare ? C'est à droite.", "A1", 5),
    ("tout droit", "straight ahead", "Continuez tout droit.", "A1", 5),
    ("près de", "near", "L'hôtel est près de la gare.", "A1", 5),
    ("loin de", "far from", "L'aéroport est loin d'ici.", "A1", 5),
    ("en face de", "opposite / across from", "La banque est en face de la poste.", "A1", 5),
    ("au coin de", "on the corner of", "C'est au coin de la rue.", "A1", 5),

    # Lesson 6 — Likes (Pattern: "J'aime [thing]. / Je n'aime pas [thing].")
    ("manger", "to eat", "J'aime manger des croissants le matin.", "A1", 6),
    ("boire", "to drink", "J'aime boire du café le matin.", "A1", 6),
    ("voyager", "to travel", "J'aime voyager en France.", "A1", 6),
    ("la musique", "music", "J'aime la musique française.", "A1", 6),
    ("le sport", "sport", "Je n'aime pas beaucoup le sport.", "A1", 6),
    ("travailler", "to work", "Je n'aime pas travailler le weekend.", "A1", 6),
    ("parler français", "to speak French", "J'aime parler français !", "A1", 6),

    # Lesson 7 — Ability (Pattern: "Je peux [verb]. / Pouvez-vous [verb] ?")
    ("m'aider", "help me", "Pouvez-vous m'aider, s'il vous plaît ?", "A1", 7),
    ("répéter", "repeat", "Pouvez-vous répéter, s'il vous plaît ?", "A1", 7),
    ("parler lentement", "speak slowly", "Pouvez-vous parler lentement ?", "A1", 7),
    ("comprendre", "to understand", "Je peux comprendre un peu de français.", "A1", 7),
    ("écrire", "to write", "Pouvez-vous écrire ça, s'il vous plaît ?", "A1", 7),
    ("payer", "to pay", "Je peux payer par carte ?", "A1", 7),
    ("réserver", "to book / reserve", "Je peux réserver une chambre ici ?", "A1", 7),

    # Lesson 8 — Having / Existing (Pattern: "J'ai [noun]. / Il y a [noun].")
    ("un problème", "a problem", "J'ai un problème avec ma chambre.", "A1", 8),
    ("de l'argent", "money", "Je n'ai pas d'argent sur moi.", "A1", 8),
    ("faim", "hunger (as in 'I'm hungry')", "J'ai faim, je voudrais manger.", "A1", 8),
    ("soif", "thirst (as in 'I'm thirsty')", "J'ai soif, je voudrais de l'eau.", "A1", 8),
    ("une réservation", "a reservation", "J'ai une réservation au nom de Martin.", "A1", 8),
    ("du temps", "time (free time)", "Il y a du temps avant le train.", "A1", 8),
    ("besoin de", "need for", "J'ai besoin d'aide, s'il vous plaît.", "A1", 8),

    # Lesson 9 — Time (Pattern: "À quelle heure [verb] ? / À [number] heures.")
    ("le train", "the train", "À quelle heure part le train ?", "A1", 9),
    ("le bus", "the bus", "À quelle heure arrive le bus ?", "A1", 9),
    ("le vol", "the flight", "À quelle heure est le vol ?", "A1", 9),
    ("le concert", "the concert", "À quelle heure commence le concert ?", "A1", 9),
    ("la piscine", "the swimming pool", "À quelle heure ouvre la piscine ?", "A1", 9),
    ("le cinéma", "the cinema", "À quelle heure commence le film ?", "A1", 9),
    ("la poste", "the post office", "À quelle heure ferme la poste ?", "A1", 9),

    # Lesson 10 — Identifying (Pattern: "Qu'est-ce que c'est ? / C'est un/une [noun].")
    ("un médicament", "medicine / a pill", "Qu'est-ce que c'est ? C'est un médicament.", "A1", 10),
    ("une chambre", "a room", "C'est une belle chambre, merci !", "A1", 10),
    ("un menu", "a menu", "Qu'est-ce que c'est ? C'est le menu du jour.", "A1", 10),
    ("un ticket", "a ticket (metro/bus)", "C'est un ticket de métro.", "A1", 10),
    ("une carte", "a card / map", "Qu'est-ce que c'est ? C'est une carte de la ville.", "A1", 10),
    ("une clé", "a key", "C'est la clé de votre chambre.", "A1", 10),
    ("un reçu", "a receipt", "Je voudrais un reçu, s'il vous plaît.", "A1", 10),

    # ── A2 ──────────────────────────────────────────────────────────────────

    # Lesson 1 — At the Restaurant
    ("commander", "to order", "Je voudrais commander, s'il vous plaît.", "A2", 1),
    ("l'addition", "the bill", "Je prends l'addition, s'il vous plaît.", "A2", 1),
    ("le plat", "dish / course", "Quel est le plat du jour ?", "A2", 1),
    ("la carte", "the menu", "Je voudrais voir la carte, s'il vous plaît.", "A2", 1),
    ("réserver", "to book", "J'ai réservé une table pour deux.", "A2", 1),
    ("le serveur", "waiter", "Le serveur est très aimable.", "A2", 1),
    ("délicieux", "delicious", "C'est délicieux, merci !", "A2", 1),

    # Lesson 2 — Directions & Transport
    ("tourner", "to turn", "Pour aller à la gare, vous tournez à gauche.", "A2", 2),
    ("tout droit", "straight ahead", "Continuez tout droit pendant 200 mètres.", "A2", 2),
    ("près de", "near", "La pharmacie est près de la gare.", "A2", 2),
    ("loin de", "far from", "L'aéroport est loin du centre-ville.", "A2", 2),
    ("le bus", "bus", "Je prends le bus tous les jours.", "A2", 2),
    ("le métro", "metro", "Le métro est plus rapide.", "A2", 2),
    ("le billet", "ticket", "J'achète un billet aller-retour.", "A2", 2),

    # Lesson 3 — Shopping
    ("acheter", "to buy", "Je cherche des chaussures à acheter.", "A2", 3),
    ("vendre", "to sell", "Ce magasin vend des livres.", "A2", 3),
    ("le prix", "price", "Combien coûte ce sac ?", "A2", 3),
    ("cher", "expensive", "Ce restaurant est trop cher.", "A2", 3),
    ("bon marché", "cheap / affordable", "Ce marché est bon marché.", "A2", 3),
    ("la taille", "size", "Je cherche la taille 40.", "A2", 3),
    ("essayer", "to try on", "Je peux essayer cette veste ?", "A2", 3),

    # Lesson 4 — Body & Health
    ("la tête", "head", "J'ai mal à la tête.", "A2", 4),
    ("le dos", "back", "J'ai mal au dos depuis hier.", "A2", 4),
    ("malade", "sick", "Je ne me sens pas bien — je suis malade.", "A2", 4),
    ("le médecin", "doctor", "Je dois aller chez le médecin.", "A2", 4),
    ("la pharmacie", "pharmacy", "Il y a une pharmacie près d'ici ?", "A2", 4),
    ("avoir mal", "to be in pain", "J'ai mal au ventre depuis ce matin.", "A2", 4),
    ("se sentir", "to feel", "Je ne me sens pas bien aujourd'hui.", "A2", 4),

    # Lesson 5 — Home & Living
    ("l'appartement", "apartment", "Dans mon appartement, il y a trois pièces.", "A2", 5),
    ("la chambre", "bedroom", "Dans ma chambre, il y a un grand lit.", "A2", 5),
    ("la cuisine", "kitchen", "Dans ma cuisine, il y a une grande table.", "A2", 5),
    ("le loyer", "rent", "J'habite à Paris et mon loyer est cher.", "A2", 5),
    ("les meubles", "furniture", "Dans mon salon, il y a de nouveaux meubles.", "A2", 5),
    ("habiter", "to live", "J'habite à Lyon depuis deux ans.", "A2", 5),
    ("le voisin", "neighbour", "Dans mon immeuble, mon voisin est très sympa.", "A2", 5),

    # Lesson 6 — Work & Study
    ("le travail", "work", "Je travaille comme développeur.", "A2", 6),
    ("le bureau", "office", "Je commence au bureau à neuf heures.", "A2", 6),
    ("la réunion", "meeting", "J'ai une réunion importante à quatorze heures.", "A2", 6),
    ("apprendre", "to learn", "Je travaille comme professeur et j'adore apprendre.", "A2", 6),
    ("étudier", "to study", "Elle travaille comme chercheuse et étudie beaucoup.", "A2", 6),
    ("le collègue", "colleague", "Je travaille avec des collègues sympathiques.", "A2", 6),
    ("le salaire", "salary", "Je commence à huit heures pour un bon salaire.", "A2", 6),

    # Lesson 7 — Hobbies & Free Time
    ("le loisir", "leisure / hobby", "J'adore mes loisirs le weekend.", "A2", 7),
    ("lire", "to read", "J'adore lire des romans le soir.", "A2", 7),
    ("le sport", "sport", "Je fais du sport trois fois par semaine.", "A2", 7),
    ("le cinéma", "cinema", "J'adore le cinéma — je vais voir un film ce soir.", "A2", 7),
    ("écouter", "to listen", "J'adore écouter de la musique en travaillant.", "A2", 7),
    ("jouer", "to play", "Je joue de la guitare deux heures par semaine.", "A2", 7),
    ("cuisiner", "to cook", "J'adore cuisiner — je fais un nouveau plat chaque semaine.", "A2", 7),

    # Lesson 8 — Emotions & Feelings
    ("content", "happy / pleased", "Je me sens content de te voir.", "A2", 8),
    ("triste", "sad", "Je me sens triste aujourd'hui.", "A2", 8),
    ("fatigué", "tired", "Ça me rend fatigué de travailler si tard.", "A2", 8),
    ("inquiet", "worried", "Je me sens inquiet pour mon examen.", "A2", 8),
    ("surpris", "surprised", "Ça me rend surpris — je n'attendais pas ça !", "A2", 8),
    ("fâché", "angry", "Ça me rend fâché quand les trains sont en retard.", "A2", 8),
    ("avoir peur", "to be afraid", "J'ai peur des araignées — ça me rend anxieux.", "A2", 8),

    # Lesson 9 — Travel & Tourism
    ("l'aéroport", "airport", "Je pars à Rome — j'ai besoin d'aller à l'aéroport.", "A2", 9),
    ("la valise", "suitcase", "Je pars pour deux semaines — j'ai besoin d'une grande valise.", "A2", 9),
    ("le passeport", "passport", "Je pars à l'étranger — j'ai besoin de mon passeport.", "A2", 9),
    ("l'office de tourisme", "tourist office", "Je pars à Lyon — j'ai besoin de l'office de tourisme.", "A2", 9),
    ("visiter", "to visit", "Je pars à Paris pour visiter le Louvre.", "A2", 9),
    ("la chambre d'hôtel", "hotel room", "J'ai besoin d'une chambre d'hôtel pour trois nuits.", "A2", 9),
    ("le voyage", "trip / journey", "Je pars en voyage — j'ai besoin de réserver.", "A2", 9),

    # Lesson 10 — Daily Routines
    ("se réveiller", "to wake up", "D'habitude, je me réveille à sept heures.", "A2", 10),
    ("se doucher", "to shower", "D'habitude, je me douche à sept heures et demie.", "A2", 10),
    ("s'habiller", "to get dressed", "D'habitude, je m'habille avant le petit-déjeuner.", "A2", 10),
    ("le petit-déjeuner", "breakfast", "D'habitude, je prends mon petit-déjeuner à huit heures.", "A2", 10),
    ("rentrer", "to return home", "D'habitude, je rentre à la maison à dix-huit heures.", "A2", 10),
    ("se coucher", "to go to bed", "D'habitude, je me couche à vingt-trois heures.", "A2", 10),
    ("la routine", "routine", "D'habitude, ma routine commence à sept heures.", "A2", 10),
]


async def seed():
    os.makedirs("../data", exist_ok=True)

    # Drop and recreate all tables — safe for development
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("OK Tables dropped and recreated")

    async with AsyncSessionLocal() as session:
        # Create hardcoded test user (id=1) — replaced by real auth later
        test_user = User(
            email="test@example.com",
            password_hash="not-a-real-hash",
            current_level="A1",
        )
        session.add(test_user)
        await session.flush()
        print("OK Test user created (id=1)")

        # Seed lesson patterns
        for level, lesson_num, pattern_fr, pattern_en, explanation, tip in LESSON_PATTERNS:
            session.add(LessonPattern(
                level=level,
                lesson_number=lesson_num,
                pattern_fr=pattern_fr,
                pattern_en=pattern_en,
                explanation=explanation,
                tip=tip,
            ))
        print(f"OK {len(LESSON_PATTERNS)} lesson patterns seeded")

        # Seed vocabulary
        for word_fr, word_en, example, level, lesson_num in VOCABULARY:
            session.add(Vocabulary(
                word_fr=word_fr,
                word_en=word_en,
                example_sentence_fr=example,
                level=level,
                lesson_number=lesson_num,
            ))
        print(f"OK {len(VOCABULARY)} vocabulary words seeded")

        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
