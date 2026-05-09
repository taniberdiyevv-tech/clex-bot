import google.generativeai as genai
import os, json

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

LEVEL_NAMES = {
    "beginner":"Boshlang'ich (A1)", "elementary":"Asosiy (A2)",
    "intermediate":"O'rta (B1)", "upper":"Yuqori O'rta (B2)",
    "advanced":"Ilg'or (C1)", "master":"Ustoz (C2)"
}

def parse_json(text):
    text = text.strip().replace("```json","").replace("```","").strip()
    return json.loads(text)

async def generate_assessment_questions(subject, count=5):
    prompt = f"""{subject} fanidan bilim darajasini aniqlash uchun {count} ta savol tuzin.
JSON: [{{"question":"...","options":["A","B","C","D"],"correct":0,"difficulty":"easy/medium/hard"}}]
Faqat JSON qaytaring. O'zbekcha."""
    try:
        r = model.generate_content(prompt)
        return parse_json(r.text)
    except:
        return []

async def assess_knowledge(subject, answers):
    prompt = f"""{subject} fanida foydalanuvchi javoblari: {answers}
JSON: {{"level":"beginner/elementary/intermediate/upper/advanced/master","score":0-100,"feedback":"...","recommendation":"..."}}
Faqat JSON. O'zbekcha."""
    try:
        r = model.generate_content(prompt)
        return parse_json(r.text)
    except:
        return {"level":"beginner","score":0,"feedback":"Boshlang'ich darajadan boshlaymiz!","recommendation":"Asoslardan o'rganamiz."}

async def get_topics(subject, level):
    level_name = LEVEL_NAMES.get(level, "Boshlang'ich")
    prompt = f"""{subject} fanining {level_name} darajasida 8 ta mavzu.
JSON: ["Mavzu 1","Mavzu 2",...] Faqat JSON. O'zbekcha."""
    try:
        r = model.generate_content(prompt)
        return parse_json(r.text)
    except:
        return ["Asosiy tushunchalar","Amaliy mashqlar","Murakkab mavzular"]

async def generate_lesson(subject, topic, level):
    level_name = LEVEL_NAMES.get(level, "Boshlang'ich")
    prompt = f"""Sen CLEX AI o'qituvchisisiz.
Fan: {subject}, Mavzu: {topic}, Daraja: {level_name}
Qisqa va chiroyli dars yozing. Emoji ishlating. Maksimal 250 so'z. O'zbekcha."""
    try:
        r = model.generate_content(prompt)
        return r.text
    except:
        return "❌ Dars yuklanmadi. Qayta urinib ko'ring."

async def generate_quiz(subject, topic, level, count=5):
    level_name = LEVEL_NAMES.get(level, "Boshlang'ich")
    prompt = f"""Sen CLEX AI o'qituvchisisiz. {subject} - {topic} ({level_name}) dan {count} ta test.
JSON: [{{"question":"...","options":["A","B","C","D"],"correct":0,"explanation":"..."}}]
Faqat JSON. O'zbekcha."""
    try:
        r = model.generate_content(prompt)
        return parse_json(r.text)
    except:
        return []

async def generate_mooc_test(subject, level):
    prompt = f"""CLEX MOOC test. {subject} fanidan 10 ta o'rta/qiyin savol.
JSON: [{{"question":"...","options":["A","B","C","D"],"correct":0,"explanation":"..."}}]
Faqat JSON. O'zbekcha."""
    try:
        r = model.generate_content(prompt)
        return parse_json(r.text)
    except:
        return []

async def generate_game_question(subject, difficulty="medium"):
    prompt = f"""{subject} fanidan 1 ta {difficulty} savol.
JSON: {{"question":"...","options":["A","B","C","D"],"correct":0,"explanation":"..."}}
Faqat JSON. O'zbekcha."""
    try:
        r = model.generate_content(prompt)
        return parse_json(r.text)
    except:
        return {}

async def chat_with_ai(user_message, subject, level, history=[]):
    level_name = LEVEL_NAMES.get(level, "Boshlang'ich")
    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in history[-5:]])
    prompt = f"""Sen CLEX AI o'qituvchisisiz. Fan: {subject}, Daraja: {level_name}
Oldingi suhbat:\n{history_text}
Foydalanuvchi: {user_message}
Qisqa, aniq, do'stona javob. Emoji ishlating. O'zbekcha."""
    try:
        r = model.generate_content(prompt)
        return r.text
    except:
        return "❌ Xatolik yuz berdi. Qayta urinib ko'ring."
