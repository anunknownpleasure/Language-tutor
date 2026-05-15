"""
Run once to create tables and seed vocabulary.
Usage: python seed.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from database import Base, engine, AsyncSessionLocal
from models import User, Vocabulary

VOCABULARY = [
    # ── A1 ──────────────────────────────────────────────────────────────────
    # Lesson 1 — Greetings & Politeness
    ("bonjour", "hello", "Bonjour, comment vous appelez-vous ?", "A1", 1),
    ("merci", "thank you", "Merci beaucoup pour votre aide.", "A1", 1),
    ("s'il vous plaît", "please", "Un café, s'il vous plaît.", "A1", 1),
    ("au revoir", "goodbye", "Au revoir, à bientôt !", "A1", 1),
    ("excusez-moi", "excuse me", "Excusez-moi, où est la gare ?", "A1", 1),
    ("oui", "yes", "Oui, je comprends.", "A1", 1),
    ("non", "no", "Non, merci.", "A1", 1),
    # Lesson 2 — Numbers
    ("un", "one", "J'ai un frère.", "A1", 2),
    ("deux", "two", "Il y a deux chaises.", "A1", 2),
    ("trois", "three", "J'ai trois chats.", "A1", 2),
    ("dix", "ten", "Il est dix heures.", "A1", 2),
    ("vingt", "twenty", "J'ai vingt ans.", "A1", 2),
    ("cent", "one hundred", "Ça coûte cent euros.", "A1", 2),
    ("combien", "how many/much", "Combien ça coûte ?", "A1", 2),
    # Lesson 3 — Family
    ("la mère", "mother", "Ma mère s'appelle Marie.", "A1", 3),
    ("le père", "father", "Mon père travaille à Paris.", "A1", 3),
    ("le frère", "brother", "J'ai un frère plus jeune.", "A1", 3),
    ("la sœur", "sister", "Ma sœur habite à Lyon.", "A1", 3),
    ("la famille", "family", "J'aime ma famille.", "A1", 3),
    ("les parents", "parents", "Mes parents sont gentils.", "A1", 3),
    ("l'enfant", "child", "C'est un enfant très curieux.", "A1", 3),
    # Lesson 4 — Colors
    ("rouge", "red", "La pomme est rouge.", "A1", 4),
    ("bleu", "blue", "Le ciel est bleu.", "A1", 4),
    ("vert", "green", "L'herbe est verte.", "A1", 4),
    ("blanc", "white", "La neige est blanche.", "A1", 4),
    ("noir", "black", "Le chat est noir.", "A1", 4),
    ("jaune", "yellow", "Le soleil est jaune.", "A1", 4),
    ("la couleur", "color", "Quelle est ta couleur préférée ?", "A1", 4),
    # Lesson 5 — Days & Time
    ("lundi", "Monday", "Je travaille lundi.", "A1", 5),
    ("vendredi", "Friday", "Le weekend commence vendredi.", "A1", 5),
    ("aujourd'hui", "today", "Aujourd'hui il fait beau.", "A1", 5),
    ("demain", "tomorrow", "Demain je vais au cinéma.", "A1", 5),
    ("l'heure", "the hour/time", "Quelle heure est-il ?", "A1", 5),
    ("le matin", "morning", "Je bois du café le matin.", "A1", 5),
    ("le soir", "evening", "On mange en famille le soir.", "A1", 5),
    # Lesson 6 — Food Basics
    ("le pain", "bread", "J'achète du pain à la boulangerie.", "A1", 6),
    ("l'eau", "water", "Je voudrais un verre d'eau.", "A1", 6),
    ("le café", "coffee", "Un café noir, s'il vous plaît.", "A1", 6),
    ("le repas", "meal", "Le repas est délicieux.", "A1", 6),
    ("manger", "to eat", "J'aime manger avec mes amis.", "A1", 6),
    ("boire", "to drink", "Il boit du jus d'orange.", "A1", 6),
    ("bon", "good/tasty", "Ce gâteau est très bon.", "A1", 6),
    # Lesson 7 — Places in Town
    ("la rue", "street", "J'habite dans cette rue.", "A1", 7),
    ("la gare", "train station", "La gare est près d'ici.", "A1", 7),
    ("le magasin", "shop", "Ce magasin vend des vêtements.", "A1", 7),
    ("l'hôtel", "hotel", "Je réserve une chambre à l'hôtel.", "A1", 7),
    ("l'école", "school", "Les enfants vont à l'école.", "A1", 7),
    ("la ville", "city/town", "Paris est une belle ville.", "A1", 7),
    ("ici", "here", "Le restaurant est ici.", "A1", 7),
    # Lesson 8 — Essential Verbs
    ("être", "to be", "Je suis étudiant.", "A1", 8),
    ("avoir", "to have", "J'ai deux chats.", "A1", 8),
    ("aller", "to go", "Je vais au marché.", "A1", 8),
    ("vouloir", "to want", "Je veux apprendre le français.", "A1", 8),
    ("pouvoir", "to be able to", "Pouvez-vous m'aider ?", "A1", 8),
    ("parler", "to speak", "Je parle un peu français.", "A1", 8),
    ("comprendre", "to understand", "Je ne comprends pas.", "A1", 8),
    # Lesson 9 — Basic Descriptions
    ("grand", "big/tall", "C'est un grand bâtiment.", "A1", 9),
    ("petit", "small/short", "J'ai un petit appartement.", "A1", 9),
    ("beau", "beautiful", "Paris est une belle ville.", "A1", 9),
    ("nouveau", "new", "J'ai un nouveau téléphone.", "A1", 9),
    ("vieux", "old", "C'est un vieux livre.", "A1", 9),
    ("facile", "easy", "Ce cours est facile.", "A1", 9),
    ("difficile", "difficult", "Le français est parfois difficile.", "A1", 9),
    # Lesson 10 — Weather & Nature
    ("le temps", "weather", "Quel temps fait-il ?", "A1", 10),
    ("il fait chaud", "it is hot", "Il fait chaud en été.", "A1", 10),
    ("il fait froid", "it is cold", "Il fait froid en hiver.", "A1", 10),
    ("la pluie", "rain", "J'aime la pluie.", "A1", 10),
    ("le soleil", "sun", "Le soleil brille aujourd'hui.", "A1", 10),
    ("le vent", "wind", "Il y a beaucoup de vent.", "A1", 10),
    ("la saison", "season", "L'automne est ma saison préférée.", "A1", 10),

    # ── A2 ──────────────────────────────────────────────────────────────────
    # Lesson 1 — At the Restaurant
    ("commander", "to order", "Je voudrais commander, s'il vous plaît.", "A2", 1),
    ("l'addition", "the bill", "L'addition, s'il vous plaît.", "A2", 1),
    ("le plat", "dish/course", "Quel est le plat du jour ?", "A2", 1),
    ("la carte", "menu", "Puis-je voir la carte ?", "A2", 1),
    ("réserver", "to book", "J'ai réservé une table pour deux.", "A2", 1),
    ("le serveur", "waiter", "Le serveur est très aimable.", "A2", 1),
    ("délicieux", "delicious", "Ce plat est délicieux.", "A2", 1),
    # Lesson 2 — Directions & Transport
    ("tourner", "to turn", "Tournez à gauche au carrefour.", "A2", 2),
    ("tout droit", "straight ahead", "Continuez tout droit.", "A2", 2),
    ("près de", "near", "La pharmacie est près de la gare.", "A2", 2),
    ("loin de", "far from", "L'aéroport est loin du centre.", "A2", 2),
    ("le bus", "bus", "Je prends le bus tous les jours.", "A2", 2),
    ("le métro", "metro", "Le métro est rapide.", "A2", 2),
    ("le billet", "ticket", "J'achète un billet aller-retour.", "A2", 2),
    # Lesson 3 — Shopping
    ("acheter", "to buy", "Je veux acheter ces chaussures.", "A2", 3),
    ("vendre", "to sell", "Ce magasin vend des livres.", "A2", 3),
    ("le prix", "price", "Quel est le prix de ce sac ?", "A2", 3),
    ("cher", "expensive", "Ce restaurant est trop cher.", "A2", 3),
    ("bon marché", "cheap", "Ce marché est bon marché.", "A2", 3),
    ("la taille", "size", "Quelle est votre taille ?", "A2", 3),
    ("essayer", "to try on", "Je peux essayer cette veste ?", "A2", 3),
    # Lesson 4 — Body & Health
    ("la tête", "head", "J'ai mal à la tête.", "A2", 4),
    ("le dos", "back", "Mon dos me fait mal.", "A2", 4),
    ("malade", "sick", "Je suis malade aujourd'hui.", "A2", 4),
    ("le médecin", "doctor", "Je vais chez le médecin demain.", "A2", 4),
    ("la pharmacie", "pharmacy", "La pharmacie est ouverte le dimanche.", "A2", 4),
    ("avoir mal", "to be in pain", "J'ai mal au ventre.", "A2", 4),
    ("se sentir", "to feel", "Je me sens mieux aujourd'hui.", "A2", 4),
    # Lesson 5 — Home & Living
    ("l'appartement", "apartment", "J'habite dans un appartement au centre.", "A2", 5),
    ("la chambre", "bedroom", "Ma chambre est au deuxième étage.", "A2", 5),
    ("la cuisine", "kitchen", "Je fais la cuisine tous les soirs.", "A2", 5),
    ("le loyer", "rent", "Mon loyer est de 800 euros par mois.", "A2", 5),
    ("les meubles", "furniture", "J'ai acheté de nouveaux meubles.", "A2", 5),
    ("habiter", "to live", "J'habite à Paris depuis deux ans.", "A2", 5),
    ("le voisin", "neighbour", "Mon voisin est très sympa.", "A2", 5),
    # Lesson 6 — Work & Study
    ("le travail", "work", "Mon travail est intéressant.", "A2", 6),
    ("le bureau", "office", "Je vais au bureau à neuf heures.", "A2", 6),
    ("la réunion", "meeting", "J'ai une réunion cet après-midi.", "A2", 6),
    ("apprendre", "to learn", "J'apprends le français depuis six mois.", "A2", 6),
    ("étudier", "to study", "Elle étudie à l'université.", "A2", 6),
    ("le collègue", "colleague", "Mes collègues sont sympathiques.", "A2", 6),
    ("le salaire", "salary", "Mon salaire est correct.", "A2", 6),
    # Lesson 7 — Hobbies & Free Time
    ("le loisir", "leisure/hobby", "Quels sont tes loisirs ?", "A2", 7),
    ("lire", "to read", "J'aime lire des romans.", "A2", 7),
    ("voyager", "to travel", "J'adore voyager en Europe.", "A2", 7),
    ("le sport", "sport", "Je fais du sport trois fois par semaine.", "A2", 7),
    ("le cinéma", "cinema", "On va au cinéma ce soir ?", "A2", 7),
    ("écouter", "to listen", "J'écoute de la musique en travaillant.", "A2", 7),
    ("jouer", "to play", "Je joue de la guitare.", "A2", 7),
    # Lesson 8 — Emotions & Feelings
    ("content", "happy", "Je suis content de te voir.", "A2", 8),
    ("triste", "sad", "Elle est triste aujourd'hui.", "A2", 8),
    ("fatigué", "tired", "Je suis très fatigué ce soir.", "A2", 8),
    ("inquiet", "worried", "Je suis inquiet pour mon examen.", "A2", 8),
    ("surpris", "surprised", "Il est surpris par la nouvelle.", "A2", 8),
    ("fâché", "angry", "Il est fâché contre moi.", "A2", 8),
    ("avoir peur", "to be afraid", "J'ai peur des araignées.", "A2", 8),
    # Lesson 9 — Travel & Tourism
    ("l'aéroport", "airport", "L'avion part de l'aéroport Charles de Gaulle.", "A2", 9),
    ("la valise", "suitcase", "Ma valise est trop lourde.", "A2", 9),
    ("le passeport", "passport", "N'oubliez pas votre passeport.", "A2", 9),
    ("l'office de tourisme", "tourist office", "L'office de tourisme donne des cartes gratuites.", "A2", 9),
    ("visiter", "to visit", "Je veux visiter le Louvre.", "A2", 9),
    ("la chambre d'hôtel", "hotel room", "Ma chambre d'hôtel est très confortable.", "A2", 9),
    ("le voyage", "trip/journey", "Ce voyage est inoubliable.", "A2", 9),
    # Lesson 10 — Daily Routines
    ("se réveiller", "to wake up", "Je me réveille à sept heures.", "A2", 10),
    ("se doucher", "to shower", "Je me douche tous les matins.", "A2", 10),
    ("s'habiller", "to get dressed", "Je m'habille avant le petit-déjeuner.", "A2", 10),
    ("le petit-déjeuner", "breakfast", "Je mange des céréales au petit-déjeuner.", "A2", 10),
    ("rentrer", "to return home", "Je rentre à la maison à dix-huit heures.", "A2", 10),
    ("se coucher", "to go to bed", "Je me couche à onze heures.", "A2", 10),
    ("la routine", "routine", "J'aime ma routine du matin.", "A2", 10),
]


async def seed():
    # Create the data/ directory if it doesn't exist
    os.makedirs("../data", exist_ok=True)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("OK Tables created")

    async with AsyncSessionLocal() as session:
        # Create hardcoded test user (id=1) — replaced by real auth later
        existing_user = await session.get(User, 1)
        if not existing_user:
            test_user = User(
                email="test@example.com",
                password_hash="not-a-real-hash",
                current_level="A1",
            )
            session.add(test_user)
            await session.flush()
            print("OK Test user created (id=1)")

        # Seed vocabulary only if table is empty
        from sqlalchemy import select, func
        count = await session.scalar(select(func.count()).select_from(Vocabulary))
        if count == 0:
            for word_fr, word_en, example, level, lesson_num in VOCABULARY:
                session.add(Vocabulary(
                    word_fr=word_fr,
                    word_en=word_en,
                    example_sentence_fr=example,
                    level=level,
                    lesson_number=lesson_num,
                ))
            await session.commit()
            print(f"OK {len(VOCABULARY)} vocabulary words seeded")
        else:
            print(f"OK Vocabulary already seeded ({count} words found)")


if __name__ == "__main__":
    asyncio.run(seed())
