import os, asyncio, logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from database import Database
from ai_tutor import (generate_assessment_questions, assess_knowledge, get_topics,
                      generate_lesson, generate_quiz, generate_mooc_test,
                      generate_game_question, chat_with_ai)

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
db = Database()
user_sessions = {}
active_games = {}

CABINETS = {
    "lang":"🗣 Til O'rganish", "math":"🔢 Matematika & Aniq Fanlar",
    "chem":"🧪 Kimyo & Biologiya", "hum":"📖 Gumanitar Fanlar",
    "soc":"🌍 Ijtimoiy Fanlar", "it":"💻 IT & Dasturlash", "art":"🎨 Ijodiy Fanlar"
}
LANGUAGES = {
    "en":"🇬🇧 Ingliz","ru":"🇷🇺 Rus","de":"🇩🇪 Nemis","fr":"🇫🇷 Fransuz",
    "ar":"🇦🇪 Arab","zh":"🇨🇳 Xitoy","ja":"🇯🇵 Yapon","ko":"🇰🇷 Koreya",
    "es":"🇪🇸 Ispan","tr":"🇹🇷 Turk","uz":"🇺🇿 O'zbek"
}
SUBJECTS = {
    "math":{"📐 Matematika":"Matematika","⚡ Fizika":"Fizika","💻 Informatika":"Informatika"},
    "chem":{"🧪 Kimyo":"Kimyo","🌿 Biologiya":"Biologiya","🔬 Anatomiya":"Anatomiya"},
    "hum":{"📜 Tarix":"Tarix","📚 Adabiyot":"Adabiyot","🧠 Psixologiya":"Psixologiya"},
    "soc":{"🌍 Geografiya":"Geografiya","💰 Iqtisodiyot":"Iqtisodiyot","⚖️ Huquq":"Huquq"},
    "it":{"🐍 Python":"Python","🌐 Web":"Web dasturlash","🤖 AI":"Sun'iy intellekt"},
    "art":{"🎨 Dizayn":"Dizayn asoslari","🎵 Musiqa":"Musiqa nazariyasi"}
}
GAME_SUBJECTS = ["Ingliz tili","Matematika","Kimyo","Biologiya","Tarix","Geografiya","Fizika","Informatika"]
LEVEL_NAMES = {
    "beginner":"Boshlang'ich (A1)","elementary":"Asosiy (A2)",
    "intermediate":"O'rta (B1)","upper":"Yuqori O'rta (B2)",
    "advanced":"Ilg'or (C1)","master":"Ustoz (C2)"
}

def s(user_id):
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    return user_sessions[user_id]

def bar(cur, total, n=10):
    f = int(n*cur/total) if total>0 else 0
    return f"{'▓'*f}{'░'*(n-f)} {int(100*cur/total) if total>0 else 0}%"

def menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 Kabinetlar",callback_data="cabinets"),
         InlineKeyboardButton("🎮 O'yinlar",callback_data="games_menu")],
        [InlineKeyboardButton("🏆 Reyting",callback_data="leaderboard"),
         InlineKeyboardButton("👤 Profilim",callback_data="profile")],
        [InlineKeyboardButton("📝 MOOC Test",callback_data="mooc_menu"),
         InlineKeyboardButton("🤖 AI Suhbat",callback_data="ai_chat")]
    ])

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.first_name, user.username)
    streak = db.update_streak(user.id)
    st = db.get_user_stats(user.id)
    xp, level = st.get("xp",0), st.get("level",1)
    await update.message.reply_text(
        f"╔══════════════════════╗\n║   🎓  C L E X  🎓    ║\n║  Bilimning Yangi Davri ║\n╚══════════════════════╝\n\n"
        f"Salom, *{user.first_name}*! 👋\n\n"
        f"⭐ Daraja: *{level}* | ✨ XP: *{xp}*\n{bar(xp%500,500)}\n🔥 Streak: *{streak} kun*\n\n"
        f"Bugun ham o'rganamizmi? 💪",
        parse_mode="Markdown", reply_markup=menu_kb()
    )

async def main_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    user = q.from_user
    st = db.get_user_stats(user.id)
    xp, level = st.get("xp",0), st.get("level",1)
    streak = st.get("streak",0)
    await q.edit_message_text(
        f"╔══════════════════════╗\n║   🎓  C L E X  🎓    ║\n╚══════════════════════╝\n\n"
        f"⭐ Daraja: *{level}* | ✨ XP: *{xp}*\n{bar(xp%500,500)}\n🔥 Streak: *{streak} kun*",
        parse_mode="Markdown", reply_markup=menu_kb()
    )

async def show_cabinets(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    kb = []; row = []
    for k,v in CABINETS.items():
        row.append(InlineKeyboardButton(v, callback_data=f"cab_{k}"))
        if len(row)==2: kb.append(row); row=[]
    if row: kb.append(row)
    kb.append([InlineKeyboardButton("🏠 Bosh sahifa",callback_data="main_menu")])
    await q.edit_message_text("📚 *Kabinetni tanlang:*\n\nHar birida o'z AI o'qituvchisi! 🤖",
                              parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def handle_cabinet(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cab = q.data.replace("cab_",""); uid = q.from_user.id
    s(uid)["cabinet"] = cab; db.set_cabinet(uid, cab)
    if cab=="lang":
        kb=[]; row=[]
        for code,name in LANGUAGES.items():
            row.append(InlineKeyboardButton(name,callback_data=f"lang_{code}"))
            if len(row)==3: kb.append(row); row=[]
        if row: kb.append(row)
        kb.append([InlineKeyboardButton("⬅️ Orqaga",callback_data="cabinets")])
        await q.edit_message_text("🗣 *Qaysi tilni o'rganmoqchisiz?*",parse_mode="Markdown",reply_markup=InlineKeyboardMarkup(kb))
    else:
        subjs = SUBJECTS.get(cab,{})
        kb=[[InlineKeyboardButton(en,callback_data=f"subj_{sn}")] for en,sn in subjs.items()]
        kb.append([InlineKeyboardButton("⬅️ Orqaga",callback_data="cabinets")])
        await q.edit_message_text(f"*{CABINETS[cab]}*\n\nFanni tanlang:",parse_mode="Markdown",reply_markup=InlineKeyboardMarkup(kb))

async def handle_language(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    code = q.data.replace("lang_",""); uid = q.from_user.id
    name = LANGUAGES.get(code,code)
    s(uid)["subject"] = name; db.set_subject(uid, name)
    await show_knowledge_check(q, name)

async def handle_subject(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    subj = q.data.replace("subj_",""); uid = q.from_user.id
    s(uid)["subject"] = subj; db.set_subject(uid, subj)
    await show_knowledge_check(q, subj)

async def show_knowledge_check(q, subject):
    kb=[
        [InlineKeyboardButton("🆕 0 dan boshlayman",callback_data="lvl_zero")],
        [InlineKeyboardButton("📚 Biroz bilaman — sinab ko'r",callback_data="lvl_test")],
        [InlineKeyboardButton("🎯 Yaxshi bilaman — darajamni aniqla",callback_data="lvl_assess")]
    ]
    await q.edit_message_text(
        f"*{subject}* bo'yicha bilim darajangiz?\n\n🤖 AI shaxsiy o'quv reja tuzadi!",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)

    
    )
async def handle_level(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id; choice = q.data; ss = s(uid)
    subject = ss.get("subject","Umumiy")
    if choice=="lvl_zero":
        db.set_knowledge_level(uid,"beginner"); ss["level"]="beginner"
        await q.edit_message_text(
            f"✅ *{subject}* ni noldan boshlaymiz!\n\n🤖 AI sizni bosqichma-bosqich o'rgatadi! 😊",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📖 Birinchi dars",callback_data="lesson_start")],
                                               [InlineKeyboardButton("🏠 Bosh sahifa",callback_data="main_menu")]]))
    else:
        await q.edit_message_text("⏳ AI savollar tayyorlamoqda...")
        questions = await generate_assessment_questions(subject, 5)
        if questions:
            ss["aq"]=questions; ss["ai"]=0; ss["aa"]=[]
            await show_assess_q(q, ss)
        else:
            db.set_knowledge_level(uid,"beginner"); ss["level"]="beginner"
            await q.edit_message_text("⚠️ Boshlang'ich darajadan boshlaymiz!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📖 Dars boshlash",callback_data="lesson_start")]]))

async def show_assess_q(q, ss):
    qs=ss["aq"]; i=ss["ai"]; total=len(qs); qdata=qs[i]
    kb=[[InlineKeyboardButton(f"{['A','B','C','D'][j]}. {opt}",callback_data=f"aq_{j}")]
        for j,opt in enumerate(qdata["options"])]
    await q.edit_message_text(
        f"📊 *Bilim darajasi aniqlash*\n{bar(i,total)}\nSavol {i+1}/{total}\n\n❓ {qdata['question']}",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def handle_assess(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id; ss = s(uid); ans = int(q.data.replace("aq_",""))
    qs=ss["aq"]; i=ss["ai"]
    correct = ans==qs[i]["correct"]
    ss["aa"].append({"question":qs[i]["question"],"correct":correct,"user_answer":qs[i]["options"][ans]})
    ss["ai"]+=1
    if ss["ai"]>=len(qs):
        await q.edit_message_text("🤖 AI natijalarni tahlil qilmoqda...")
        result = await assess_knowledge(ss.get("subject","Umumiy"), ss["aa"])
        level=result.get("level","beginner"); score=result.get("score",0)
        feedback=result.get("feedback",""); rec=result.get("recommendation","")
        db.set_knowledge_level(uid,level); ss["level"]=level
        await q.edit_message_text(
            f"🎯 *Natija!*\n\n📊 Ball: *{score}/100*\n🏅 Daraja: *{LEVEL_NAMES.get(level,level)}*\n\n💬 {feedback}\n\n📚 {rec}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📖 Darsni boshlash",callback_data="lesson_start")],
                                               [InlineKeyboardButton("🏠 Bosh sahifa",callback_data="main_menu")]]))
    else:
        await show_assess_q(q, ss)

async def lesson_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id; ss = s(uid)
    subject=ss.get("subject","Umumiy"); level=ss.get("level","beginner")
    await q.edit_message_text("📚 AI dars tayyorlamoqda...")
    topics = await get_topics(subject, level)
    ss["topics"]=topics; ss["ti"]=0
    if topics:
        topic=topics[0]; ss["topic"]=topic
        lesson = await generate_lesson(subject,topic,level)
        db.add_xp(uid,10); db.add_badge(uid,"🎓 Birinchi Dars")
        await q.edit_message_text(
            f"📖 *{topic}*\n\n{lesson}\n\n✨ +10 XP!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Test",callback_data="do_quiz"),
                 InlineKeyboardButton("➡️ Keyingi",callback_data="next_topic")],
                [InlineKeyboardButton("🤖 AI dan so'rash",callback_data="ai_chat"),
                 InlineKeyboardButton("🏠 Bosh sahifa",callback_data="main_menu")]]))

async def next_topic(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id; ss = s(uid)
    topics=ss.get("topics",[]); idx=ss.get("ti",0)+1; ss["ti"]=idx
    if idx>=len(topics):
        await q.edit_message_text("🎉 *Barcha mavzularni tugatdingiz!*",parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📝 MOOC Test",callback_data="mooc_menu")],
                                               [InlineKeyboardButton("🏠 Bosh sahifa",callback_data="main_menu")]])); return
    subject=ss.get("subject","Umumiy"); level=ss.get("level","beginner")
    topic=topics[idx]; ss["topic"]=topic
    await q.edit_message_text("📚 Keyingi dars tayyorlanmoqda...")
    lesson = await generate_lesson(subject,topic,level)
    db.add_xp(uid,10)
    await q.edit_message_text(
        f"📖 *{topic}* ({idx+1}/{len(topics)})\n\n{lesson}\n\n✨ +10 XP!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Test",callback_data="do_quiz"),
             InlineKeyboardButton("➡️ Keyingi",callback_data="next_topic")],
            [InlineKeyboardButton("🏠 Bosh sahifa",callback_data="main_menu")]]))

async def do_quiz(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id; ss = s(uid)
    subject=ss.get("subject","Umumiy"); topic=ss.get("topic",subject); level=ss.get("level","beginner")
    await q.edit_message_text("📝 Test savollar tayyorlanmoqda...")
    questions = await generate_quiz(subject,topic,level,5)
    if not questions:
        await q.edit_message_text("❌ Test yuklanmadi."); return
    ss["qq"]=questions; ss["qi"]=0; ss["qs"]=0
    await show_quiz_q(q,ss)

async def show_quiz_q(q,ss):
    qs=ss["qq"]; i=ss["qi"]; total=len(qs); score=ss["qs"]; qdata=qs[i]
    kb=[[InlineKeyboardButton(f"{['A','B','C','D'][j]}. {opt}",callback_data=f"qz_{j}")]
        for j,opt in enumerate(qdata["options"])]
    await q.edit_message_text(
        f"📝 *Test*\n{bar(i,total)}\nSavol {i+1}/{total} | Ball: {score}\n\n❓ {qdata['question']}",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def handle_quiz(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id; ss = s(uid); ans = int(q.data.replace("qz_",""))
    qs=ss["qq"]; i=ss["qi"]; qdata=qs[i]
    correct = ans==qdata["correct"]
    if correct: ss["qs"]+=1; fb=f"✅ *To'g'ri!*\n\n💡 {qdata.get('explanation','')}"
    else: fb=f"❌ *Noto'g'ri!*\nTo'g'ri: *{qdata['options'][qdata['correct']]}*\n\n💡 {qdata.get('explanation','')}"
    ss["qi"]+=1
    if ss["qi"]>=len(qs):
        score=ss["qs"]; total=len(qs); xp=score*20
        db.save_test_result(uid,ss.get("cabinet",""),ss.get("subject",""),score,total)
        db.add_xp(uid,xp)
        if score==total: db.add_badge(uid,"🧠 Test Ustasi")
        await q.edit_message_text(
            f"{fb}\n\n━━━━━━━━━━━━\n🎯 *Natija*\n{bar(score,total)}\n✅ {score}/{total} | ✨ +{xp} XP\n\n{'🏆 Mukammal!' if score==total else '💪 Davom eting!'}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Qayta test",callback_data="do_quiz"),
                 InlineKeyboardButton("➡️ Keyingi dars",callback_data="next_topic")],
                [InlineKeyboardButton("🏠 Bosh sahifa",callback_data="main_menu")]]))
    else:
        next_q=qs[ss["qi"]]
        kb=[[InlineKeyboardButton(f"{['A','B','C','D'][j]}. {opt}",callback_data=f"qz_{j}")]
            for j,opt in enumerate(next_q["options"])]
        await q.edit_message_text(
            f"{fb}\n\n━━━━━━━━━━━━\n📝 Savol {ss['qi']+1}/{len(qs)}\n\n❓ {next_q['question']}",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def mooc_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    kb=[[InlineKeyboardButton(s,callback_data=f"mooc_{s}")] for s in GAME_SUBJECTS]
    kb.append([InlineKeyboardButton("🏠 Bosh sahifa",callback_data="main_menu")])
    await q.edit_message_text(
        "📝 *Haftalik MOOC Test*\n\nHar *Yakshanba* yangi test!\n🥇90%+ Oltin | 🥈70%+ Kumush | 🥉50%+ Bronza\n\nFan tanlang:",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def start_mooc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    subject=q.data.replace("mooc_",""); uid=q.from_user.id; ss=s(uid)
    await q.edit_message_text(f"⏳ *{subject}* uchun MOOC test tayyorlanmoqda...")
    questions = await generate_mooc_test(subject,"intermediate")
    if not questions:
        await q.edit_message_text("❌ Test yuklanmadi."); return
    ss["mq"]=questions; ss["ms"]=subject; ss["mi"]=0; ss["msc"]=0
    await show_mooc_q(q,ss)

async def show_mooc_q(q,ss):
    qs=ss["mq"]; i=ss["mi"]; total=len(qs); score=ss["msc"]; qdata=qs[i]
    kb=[[InlineKeyboardButton(f"{['A','B','C','D'][j]}. {opt}",callback_data=f"ma_{j}")]
        for j,opt in enumerate(qdata["options"])]
    await q.edit_message_text(
        f"📝 *MOOC Test*\n{bar(i,total)}\nSavol {i+1}/{total} | Ball: {score}\n\n❓ {qdata['question']}",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def handle_mooc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid=q.from_user.id; ss=s(uid); ans=int(q.data.replace("ma_",""))
    qs=ss["mq"]; i=ss["mi"]
    if ans==qs[i]["correct"]: ss["msc"]+=1
    ss["mi"]+=1
    if ss["mi"]>=len(qs):
        score=ss["msc"]; total=len(qs); subject=ss.get("ms","")
        cert=db.save_mooc_result(uid,subject,score,total); xp=score*30
        db.add_xp(uid,xp)
        pct=int(score/total*100)
        await q.edit_message_text(
            f"🎓 *MOOC Natija*\n━━━━━━━━━━━━\n📚 {subject}\n{bar(score,total)}\n✅ {score}/{total} ({pct}%)\n🏅 {cert}\n✨ +{xp} XP",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📚 Dars o'rganish",callback_data="cabinets")],
                                               [InlineKeyboardButton("🏠 Bosh sahifa",callback_data="main_menu")]]))
    else:
        await show_mooc_q(q,ss)

async def games_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    kb=[
        [InlineKeyboardButton("🎯 Viktorina",callback_data="gi_viktorin"),
         InlineKeyboardButton("⚔️ Duello",callback_data="gi_duel")],
        [InlineKeyboardButton("💀 Survival",callback_data="gi_survival"),
         InlineKeyboardButton("⚡ Speed Round",callback_data="gi_speed")],
        [InlineKeyboardButton("🏆 Turnir",callback_data="gi_turnir"),
         InlineKeyboardButton("👥 Jamoa Jangi",callback_data="gi_team")],
        [InlineKeyboardButton("🏠 Bosh sahifa",callback_data="main_menu")]
    ]
    await q.edit_message_text("🎮 *O'yinlar*\n\nGuruhga olib boring va do'stlaringiz bilan o'ynang! 🔥",
                              parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def game_info(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    gtype=q.data.replace("gi_","")
    infos={
        "viktorin":"🎯 *Viktorina*\nGuruhda barcha qatnashadi!\n\nGuruhda: `/viktorin [fan]`",
        "duel":"⚔️ *Duello*\n1v1 bellashuv! 10 savol.\n\nGuruhda: `/duel`",
        "survival":"💀 *Survival*\nNoto'g'ri = chiqib ketish!\n\nGuruhda: `/survival [fan]`",
        "speed":"⚡ *Speed Round*\n60 sekund, imkon qadar ko'p!\n\nGuruhda: `/speed [fan]`",
        "turnir":"🏆 *Haftalik Turnir*\n🔜 Tez kunda...",
        "team":"👥 *Jamoa Jangi*\nGuruh ikki jamoaga!\n\nGuruhda: `/team`"
    }
    await q.edit_message_text(infos.get(gtype,""),parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎮 O'yinlar",callback_data="games_menu")],
                                           [InlineKeyboardButton("🏠 Bosh sahifa",callback_data="main_menu")]]))

async def cmd_viktorin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id=update.effective_chat.id
    if chat_id>0:
        await update.message.reply_text("❌ Faqat guruhda!"); return
    import random
    args=ctx.args; subject=" ".join(args) if args else random.choice(GAME_SUBJECTS)
    active_games[chat_id]={"type":"viktorin","subject":subject,"players":{},"scores":{},"active":False}
    kb=[[InlineKeyboardButton("✋ Qo'shilish",callback_data=f"join_{chat_id}")]]
    await update.message.reply_text(
        f"🎯 *CLEX Viktorina!*\n\n📚 Fan: *{subject}*\n\n30 sekund ichida qo'shiling!",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    await asyncio.sleep(30)
    game=active_games.get(chat_id)
    if not game or game["active"]: return
    if not game["players"]:
        await ctx.bot.send_message(chat_id,"❌ O'yinchi yo'q.")
        active_games.pop(chat_id,None); return
    game["active"]=True
    await run_viktorin(ctx.bot, chat_id, game, subject)

async def join_game(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    chat_id=int(q.data.replace("join_","")); user=q.from_user
    game=active_games.get(chat_id)
    if game and not game["active"]:
        game["players"][user.id]=user.first_name
        game["scores"][user.id]=0
        await q.answer(f"✅ {user.first_name} qo'shildi!",show_alert=True)

async def run_viktorin(bot, chat_id, game, subject):
    import random
    for rnd in range(10):
        if chat_id not in active_games: return
        subj=random.choice(GAME_SUBJECTS) if subject=="Aralash" else subject
        question=await generate_game_question(subj)
        if not question: continue
        game["current_q"]=question; game["answered"]=set()
        game["start_time"]=datetime.now()
        kb=[[InlineKeyboardButton(f"{['A','B','C','D'][i]}. {opt}",callback_data=f"vans_{i}_{chat_id}")]
            for i,opt in enumerate(question["options"])]
        await bot.send_message(chat_id,f"❓ *Savol {rnd+1}/10*\n\n{question['question']}\n\n⏱ 30 sekund!",
                               parse_mode="Markdown",reply_markup=InlineKeyboardMarkup(kb))
        await asyncio.sleep(30)
        correct=question["options"][question["correct"]]
        await bot.send_message(chat_id,f"✅ To'g'ri javob: *{correct}*",parse_mode="Markdown")
        await asyncio.sleep(3)
    game=active_games.pop(chat_id,None)
    if not game: return
    scores=sorted(game["scores"].items(),key=lambda x:x[1],reverse=True)
    medals=["🥇","🥈","🥉"]
    lb="\n".join([f"{medals[i] if i<3 else str(i+1)+'.'} {game['players'].get(uid,'?')}: {sc} ball" for i,(uid,sc) in enumerate(scores[:5])])
    await bot.send_message(chat_id,f"🏆 *Viktorina tugadi!*\n\n{lb}\n\n🎮 Qayta: /viktorin",parse_mode="Markdown")

async def viktorin_answer(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    parts=q.data.split("_"); ans=int(parts[1]); chat_id=int(parts[2]); user=q.from_user
    game=active_games.get(chat_id)
    if not game: await q.answer("O'yin tugagan."); return
    if user.id in game.get("answered",set()):
        await q.answer("Allaqachon javob berdingiz!"); return
    game["answered"].add(user.id)
    qdata=game.get("current_q",{})
    if ans==qdata.get("correct",999):
        elapsed=int((datetime.now()-game["start_time"]).total_seconds())
        pts=max(10,30-elapsed); game["scores"][user.id]=game["scores"].get(user.id,0)+pts
        db.add_xp(user.id,pts); await q.answer(f"✅ To'g'ri! +{pts} ball!")
    else:
        await q.answer("❌ Noto'g'ri!")

async def show_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); uid=q.from_user.id
    st=db.get_user_stats(uid); badges=db.get_badges(uid)
    xp,level,streak=st.get("xp",0),st.get("level",1),st.get("streak",0)
    badge_text="\n".join([f"  {b[0]}" for b in badges]) or "  Hali badge yo'q"
    await q.edit_message_text(
        f"👤 *Profilim*\n━━━━━━━━━━━━\n⭐ Daraja: *{level}*\n✨ XP: *{xp}*\n{bar(xp%500,500)}\n🔥 Streak: *{streak} kun*\n📚 Fan: {st.get('subject','—')}\n\n🏅 *Badgelar:*\n{badge_text}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Bosh sahifa",callback_data="main_menu")]]))

async def show_leaderboard(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    leaders=db.get_leaderboard(10); medals=["🥇","🥈","🥉"]
    text="🏆 *Top O'quvchilar*\n━━━━━━━━━━━━\n"
    for i,(name,xp,level,streak) in enumerate(leaders):
        text+=f"{medals[i] if i<3 else str(i+1)+'.'} *{name}* — {xp} XP | Daraja {level} | 🔥{streak}\n"
    if not leaders: text+="Hali hech kim yo'q. Birinchi bo'ling! 🚀"
    await q.edit_message_text(text,parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Bosh sahifa",callback_data="main_menu")]]))

async def ai_chat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); uid=q.from_user.id; ss=s(uid)
    ss["mode"]="chat"; ss["history"]=[]; subject=ss.get("subject","Umumiy")
    await q.edit_message_text(
        f"🤖 *AI O'qituvchi*\n\n*{subject}* bo'yicha savol bering!\n\n_Chiqish: /stop_",
        parse_mode="Markdown")

async def handle_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; ss=s(uid); text=update.message.text
    if ss.get("mode")=="chat":
        subject=ss.get("subject","Umumiy"); level=ss.get("level","beginner")
        history=ss.get("history",[])
        reply=await chat_with_ai(text,subject,level,history)
        history.append({"role":"user","content":text})
        history.append({"role":"assistant","content":reply})
        ss["history"]=history[-10:]; db.add_xp(uid,2)
        await update.message.reply_text(reply,parse_mode="Markdown")
    else:
        await update.message.reply_text("Menyu uchun /start bosing 😊",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Bosh sahifa",callback_data="main_menu")]]))

async def stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; s(uid)["mode"]=None
    await update.message.reply_text("✅ Tugatildi.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Bosh sahifa",callback_data="main_menu")]]))

def main():
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("stop",stop))
    app.add_handler(CommandHandler("viktorin",cmd_viktorin))
    app.add_handler(CallbackQueryHandler(main_menu,pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(show_cabinets,pattern="^cabinets$"))
    app.add_handler(CallbackQueryHandler(handle_cabinet,pattern="^cab_"))
    app.add_handler(CallbackQueryHandler(handle_language,pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(handle_subject,pattern="^subj_"))
    app.add_handler(CallbackQueryHandler(handle_level,pattern="^lvl_"))
    app.add_handler(CallbackQueryHandler(handle_assess,pattern="^aq_"))
    app.add_handler(CallbackQueryHandler(lesson_start,pattern="^lesson_start$"))
    app.add_handler(CallbackQueryHandler(next_topic,pattern="^next_topic$"))
    app.add_handler(CallbackQueryHandler(do_quiz,pattern="^do_quiz$"))
    app.add_handler(CallbackQueryHandler(handle_quiz,pattern="^qz_"))
    app.add_handler(CallbackQueryHandler(mooc_menu,pattern="^mooc_menu$"))
    app.add_handler(CallbackQueryHandler(start_mooc,pattern="^mooc_(?!ans)"))
    app.add_handler(CallbackQueryHandler(handle_mooc,pattern="^ma_"))
    app.add_handler(CallbackQueryHandler(games_menu,pattern="^games_menu$"))
    app.add_handler(CallbackQueryHandler(game_info,pattern="^gi_"))
    app.add_handler(CallbackQueryHandler(join_game,pattern="^join_"))
    app.add_handler(CallbackQueryHandler(viktorin_answer,pattern="^vans_"))
    app.add_handler(CallbackQueryHandler(show_profile,pattern="^profile$"))
    app.add_handler(CallbackQueryHandler(show_leaderboard,pattern="^leaderboard$"))
    app.add_handler(CallbackQueryHandler(ai_chat,pattern="^ai_chat$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    print("🚀 CLEX ishga tushdi!")
    app.run_polling()

if __name__=="__main__":
    main()
