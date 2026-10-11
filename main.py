import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)

import config
import db

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- HOLATLAR (FSM) ---
class TeacherAddQuestion(StatesGroup):
    waiting_for_text = State()
    waiting_for_opt_a = State()
    waiting_for_opt_b = State()
    waiting_for_opt_c = State()
    waiting_for_opt_d = State()
    waiting_for_correct = State()

class TeacherBatchAdd(StatesGroup):
    waiting_for_batch_text = State()

class StudentQuiz(StatesGroup):
    answering = State()


# --- KLAVIATURALAR ---
def teacher_main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Test qo'shish (Bittalab)"), KeyboardButton(text="📥 Bir nechta test qo'shish")],
            [KeyboardButton(text="📋 Barcha testlarni ko'rish"), KeyboardButton(text="📊 O'quvchilar natijalari")],
            [KeyboardButton(text="🗑 Barcha testlarni tozalash"), KeyboardButton(text="🔄 Natijalarni tozalash")],
            [KeyboardButton(text="🧪 Test topshirib ko'rish")]
        ],
        resize_keyboard=True
    )

def student_main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚀 Testni boshlash")],
            [KeyboardButton(text="ℹ️ Bot haqida")]
        ],
        resize_keyboard=True
    )

def quiz_options_kb(q_index: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="A", callback_data=f"ans:{q_index}:A"),
                InlineKeyboardButton(text="B", callback_data=f"ans:{q_index}:B"),
            ],
            [
                InlineKeyboardButton(text="C", callback_data=f"ans:{q_index}:C"),
                InlineKeyboardButton(text="D", callback_data=f"ans:{q_index}:D"),
            ]
        ]
    )

def correct_choice_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="A", callback_data="set_correct:A"),
                InlineKeyboardButton(text="B", callback_data="set_correct:B"),
                InlineKeyboardButton(text="C", callback_data="set_correct:C"),
                InlineKeyboardButton(text="D", callback_data="set_correct:D"),
            ]
        ]
    )


def is_teacher(user_id: int) -> bool:
    teachers = getattr(config, "TEACHER_IDS", [])
    if hasattr(config, "TEACHER_ID"):
        teachers = list(teachers) + [config.TEACHER_ID]
    # Har qanday holat uchun int va str solishtiramiz
    return int(user_id) in [int(tid) for tid in teachers]

# --- /START KOMANDASI ---
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    logging.info(f"User {user_id} ({message.from_user.full_name}) /start bosdi. is_teacher={is_teacher(user_id)}")
    
    if is_teacher(user_id):
        await message.answer(
            f"Assalomu alaykum, Hurmatli O'qituvchi! 👨‍🏫\n\n"
            f"Siz bot boshqaruv panelidasiz. Testlar qo'shishingiz, ko'rishingiz va o'quvchilar natijalarini kuzatishingiz mumkin.",
            reply_markup=teacher_main_kb()
        )
    else:
        await message.answer(
            f"Assalomu alaykum, {message.from_user.full_name}! 👋\n\n"
            f"Test tizimiga xush kelibsiz. Bilimingizni sinash uchun '🚀 Testni boshlash' tugmasini bosing.",
            reply_markup=student_main_kb()
        )


# ==================== O'QITUVCHI BO'LIMI ====================

@dp.message(F.text == "➕ Test qo'shish (Bittalab)")
async def start_add_question(message: Message, state: FSMContext):
    if not is_teacher(message.from_user.id):
        return
    await state.set_state(TeacherAddQuestion.waiting_for_text)
    await message.answer("1-qadam: Savol matnini yozing:")

@dp.message(TeacherAddQuestion.waiting_for_text)
async def process_question_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    await state.set_state(TeacherAddQuestion.waiting_for_opt_a)
    await message.answer("2-qadam: A variantini kiriting:")

@dp.message(TeacherAddQuestion.waiting_for_opt_a)
async def process_opt_a(message: Message, state: FSMContext):
    await state.update_data(opt_a=message.text)
    await state.set_state(TeacherAddQuestion.waiting_for_opt_b)
    await message.answer("3-qadam: B variantini kiriting:")

@dp.message(TeacherAddQuestion.waiting_for_opt_b)
async def process_opt_b(message: Message, state: FSMContext):
    await state.update_data(opt_b=message.text)
    await state.set_state(TeacherAddQuestion.waiting_for_opt_c)
    await message.answer("4-qadam: C variantini kiriting:")

@dp.message(TeacherAddQuestion.waiting_for_opt_c)
async def process_opt_c(message: Message, state: FSMContext):
    await state.update_data(opt_c=message.text)
    await state.set_state(TeacherAddQuestion.waiting_for_opt_d)
    await message.answer("5-qadam: D variantini kiriting:")

@dp.message(TeacherAddQuestion.waiting_for_opt_d)
async def process_opt_d(message: Message, state: FSMContext):
    await state.update_data(opt_d=message.text)
    await state.set_state(TeacherAddQuestion.waiting_for_correct)
    await message.answer(
        "6-qadam: Qaysi variant to'g'ri javob ekanligini tanlang:",
        reply_markup=correct_choice_kb()
    )

@dp.callback_query(TeacherAddQuestion.waiting_for_correct, F.data.startswith("set_correct:"))
async def process_correct_choice(callback: CallbackQuery, state: FSMContext):
    correct_opt = callback.data.split(":")[1]
    data = await state.get_data()
    
    options = {
        "A": data["opt_a"],
        "B": data["opt_b"],
        "C": data["opt_c"],
        "D": data["opt_d"]
    }
    
    qid = db.add_question(data["text"], options, correct_opt)
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        f"✅ Test muvaffaqiyatli saqlandi! (ID: {qid})\n\n"
        f"❓ Savol: {data['text']}\n"
        f"A) {options['A']}\n"
        f"B) {options['B']}\n"
        f"C) {options['C']}\n"
        f"D) {options['D']}\n"
        f"🎯 To'g'ri javob: {correct_opt}",
        reply_markup=teacher_main_kb()
    )


# --- BIR NECHTA TEST QO'SHISH (BATCH FORMAT) ---
@dp.message(F.text == "📥 Bir nechta test qo'shish")
async def start_batch_add(message: Message, state: FSMContext):
    if not is_teacher(message.from_user.id):
        return
    await state.set_state(TeacherBatchAdd.waiting_for_batch_text)
    guide = (
        "✍️ Bir nechta testni birdaniga quyidagi formatda yuboring:\n\n"
        "1. O'zbekiston poytaxti qaysi shahar?\n"
        "A) Samarqand\n"
        "B) Toshkent\n"
        "C) Buxoro\n"
        "D) Xiva\n"
        "Javob: B\n\n"
        "---\n\n"
        "2. 2 + 2 nechiga teng?\n"
        "A) 3\n"
        "B) 5\n"
        "C) 4\n"
        "D) 6\n"
        "Javob: C\n\n"
        "(Savollar orasini --- yoki bo'sh qator bilan ajratishingiz mumkin. Har birida A), B), C), D) va 'Javob: X' bo'lishi shart!)"
    )
    await message.answer(guide)

@dp.message(TeacherBatchAdd.waiting_for_batch_text)
async def process_batch_add(message: Message, state: FSMContext):
    text = message.text
    blocks = [b.strip() for b in text.split("---") if b.strip()]
    if len(blocks) == 1 and "\n\n" in text:
        blocks = [b.strip() for b in text.split("\n\n") if "Javob:" in b or "javob:" in b]

    added_count = 0
    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if len(lines) < 6:
            continue
        
        q_text = lines[0]
        # Raqamlarni tozalash (1. Savol -> Savol)
        if q_text and q_text[0].isdigit() and "." in q_text[:4]:
            q_text = q_text.split(".", 1)[1].strip()
        
        opts = {}
        ans = None
        for line in lines[1:]:
            lower = line.lower()
            if lower.startswith("a)") or lower.startswith("a."):
                opts["A"] = line[2:].strip(" .)")
            elif lower.startswith("b)") or lower.startswith("b."):
                opts["B"] = line[2:].strip(" .)")
            elif lower.startswith("c)") or lower.startswith("c."):
                opts["C"] = line[2:].strip(" .)")
            elif lower.startswith("d)") or lower.startswith("d."):
                opts["D"] = line[2:].strip(" .)")
            elif "javob:" in lower:
                ans = line.split(":")[-1].strip().upper()
                if ans and ans[0] in ["A", "B", "C", "D"]:
                    ans = ans[0]

        if len(opts) == 4 and ans in ["A", "B", "C", "D"]:
            db.add_question(q_text, opts, ans)
            added_count += 1

    await state.clear()
    await message.answer(f"🎉 Jami {added_count} ta yangi test bazaga kiritildi!", reply_markup=teacher_main_kb())


# --- BARCHA TESTLARNI KO'RISH VA O'CHIRISH ---
@dp.message(F.text == "📋 Barcha testlarni ko'rish")
async def show_all_questions(message: Message):
    if not is_teacher(message.from_user.id):
        return
    questions = db.get_questions()
    if not questions:
        await message.answer("Bazada hozircha testlar mavjud emas.")
        return

    await message.answer(f"📚 Bazadagi jami testlar soni: {len(questions)} ta")
    for idx, q in enumerate(questions, 1):
        del_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"del_q:{q['id']}")]
            ]
        )
        msg = (
            f"<b>{idx}-savol (ID: {q['id']})</b>\n"
            f"{q['text']}\n\n"
            f"A) {q['options'].get('A', '')}\n"
            f"B) {q['options'].get('B', '')}\n"
            f"C) {q['options'].get('C', '')}\n"
            f"D) {q['options'].get('D', '')}\n\n"
            f"🎯 <b>To'g'ri javob:</b> {q['correct']}"
        )
        await message.answer(msg, parse_mode="HTML", reply_markup=del_kb)

@dp.callback_query(F.data.startswith("del_q:"))
async def process_delete_question(callback: CallbackQuery):
    if not is_teacher(callback.from_user.id):
        return
    qid = int(callback.data.split(":")[1])
    success = db.delete_question(qid)
    if success:
        await callback.message.edit_text("❌ Ushbu test o'chirildi.")
    else:
        await callback.answer("Savol topilmadi yoki allaqachon o'chirilgan.")


# --- O'QUVCHILAR NATIJALARI ---
@dp.message(F.text == "📊 O'quvchilar natijalari")
async def show_results(message: Message):
    if not is_teacher(message.from_user.id):
        return
    results = db.get_results()
    if not results:
        await message.answer("Hozircha hech qaysi o'quvchi test topshirmadi.")
        return

    text = f"📊 <b>O'quvchilar natijalari (Jami: {len(results)} ta urinish):</b>\n\n"
    for idx, r in enumerate(reversed(results[-30:]), 1):  # Oxirgi 30 tasi
        uname = f"@{r['username']}" if r.get("username") else "username yo'q"
        percent = round((r['score'] / r['total']) * 100) if r['total'] > 0 else 0
        text += (
            f"<b>{idx}. {r['full_name']}</b> ({uname})\n"
            f"🎯 Ball: <b>{r['score']}/{r['total']}</b> ({percent}%)\n"
            f"--------------------------\n"
        )
    await message.answer(text, parse_mode="HTML")


# --- TOZALASH AMALLARI ---
@dp.message(F.text == "🗑 Barcha testlarni tozalash")
async def clear_questions_prompt(message: Message):
    if not is_teacher(message.from_user.id):
        return
    confirm_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Ha, barchasini o'chirish", callback_data="confirm_clear_all_q"),
                InlineKeyboardButton(text="Bekor qilish", callback_data="cancel_action")
            ]
        ]
    )
    await message.answer("⚠️ Haqiqatan ham bazadagi BARCHA testlarni o'chirib yubormoqchimisiz?", reply_markup=confirm_kb)

@dp.callback_query(F.data == "confirm_clear_all_q")
async def do_clear_questions(callback: CallbackQuery):
    if not is_teacher(callback.from_user.id):
        return
    db.clear_all_questions()
    await callback.message.edit_text("✅ Barcha testlar muvaffaqiyatli tozalandi.")

@dp.message(F.text == "🔄 Natijalarni tozalash")
async def clear_results_prompt(message: Message):
    if not is_teacher(message.from_user.id):
        return
    confirm_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Ha, natijalarni tozalash", callback_data="confirm_clear_res"),
                InlineKeyboardButton(text="Bekor qilish", callback_data="cancel_action")
            ]
        ]
    )
    await message.answer("⚠️ Barcha o'quvchilarning natijalar tarixini tozalashni xohlaysizmi?", reply_markup=confirm_kb)

@dp.callback_query(F.data == "confirm_clear_res")
async def do_clear_results(callback: CallbackQuery):
    if not is_teacher(callback.from_user.id):
        return
    db.clear_results()
    await callback.message.edit_text("✅ Barcha natijalar tozalandi.")

@dp.callback_query(F.data == "cancel_action")
async def do_cancel(callback: CallbackQuery):
    await callback.message.delete()


# ==================== O'QUVCHI / TEST TOPSHIRISH BO'LIMI ====================

@dp.message(F.text.in_(["🚀 Testni boshlash", "🧪 Test topshirib ko'rish"]))
async def start_quiz(message: Message, state: FSMContext):
    questions = db.get_questions()
    if not questions:
        await message.answer("⚠️ Hozircha bazada testlar mavjud emas. Iltimos, o'qituvchi test qo'shishini kuting.")
        return

    # Holatni boshlash
    await state.set_state(StudentQuiz.answering)
    await state.update_data(
        current_index=0,
        user_answers={},  # index -> tanlangan variant
        questions=questions
    )

    await send_quiz_step(message.chat.id, 0, questions)

async def send_quiz_step(chat_id: int, index: int, questions: list):
    q = questions[index]
    total = len(questions)
    text = (
        f"📝 <b>Savol {index + 1} / {total}</b>\n\n"
        f"<b>{q['text']}</b>\n\n"
        f"A) {q['options'].get('A', '')}\n"
        f"B) {q['options'].get('B', '')}\n"
        f"C) {q['options'].get('C', '')}\n"
        f"D) {q['options'].get('D', '')}\n\n"
        f"<i>Quyidagi tugmalardan birini tanlang:</i>"
    )
    await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=quiz_options_kb(index))

@dp.callback_query(StudentQuiz.answering, F.data.startswith("ans:"))
async def process_quiz_answer(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    q_index = int(parts[1])
    choice = parts[2]

    data = await state.get_data()
    curr = data.get("current_index", 0)
    questions = data.get("questions", [])

    if q_index != curr:
        await callback.answer("Bu savolga allaqachon javob berilgan.")
        return

    user_answers = data.get("user_answers", {})
    user_answers[curr] = choice
    await state.update_data(user_answers=user_answers)

    # Tugmani bosilganini belgilash
    await callback.answer(f"Siz {choice} variantini tanladingiz!")
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    next_index = curr + 1
    if next_index < len(questions):
        await state.update_data(current_index=next_index)
        await send_quiz_step(callback.message.chat.id, next_index, questions)
    else:
        # Barcha savollar tugadi - Yakuniy tekshirish va natija
        await finish_quiz(callback.from_user, callback.message.chat.id, questions, user_answers, state)

async def finish_quiz(user, chat_id: int, questions: list, user_answers: dict, state: FSMContext):
    await state.clear()
    score = 0
    total = len(questions)
    details = []

    report_lines = []
    for idx, q in enumerate(questions):
        user_choice = user_answers.get(idx, "-")
        correct_choice = q.get("correct", "")
        is_correct = (user_choice == correct_choice)

        if is_correct:
            score += 1
            status_icon = "✅"
        else:
            status_icon = "❌"

        details.append({
            "question_id": q["id"],
            "question": q["text"],
            "user_choice": user_choice,
            "correct_choice": correct_choice,
            "is_correct": is_correct
        })

        report_lines.append(
            f"<b>{idx + 1}-savol:</b> {status_icon}\n"
            f"Sizning javobingiz: <b>{user_choice}</b> | To'g'ri javob: <b>{correct_choice}</b>"
        )

    # Natijani saqlash
    db.save_result(
        user_id=user.id,
        full_name=user.full_name,
        username=user.username,
        score=score,
        total=total,
        details=details
    )

    percent = round((score / total) * 100) if total > 0 else 0
    emoji = "🏆" if percent >= 80 else ("👍" if percent >= 50 else "📚")

    result_msg = (
        f"{emoji} <b>TEST YAKUNLANDI!</b>\n\n"
        f"👤 <b>O'quvchi:</b> {user.full_name}\n"
        f"🎯 <b>Natija:</b> {score} / {total} ball ({percent}%)\n\n"
        f"<b>Batafsil tekshirish natijalari:</b>\n" +
        "\n".join(report_lines)
    )

    kb = teacher_main_kb() if is_teacher(user.id) else student_main_kb()
    await bot.send_message(chat_id=chat_id, text=result_msg, parse_mode="HTML", reply_markup=kb)

    # O'qituvchilarga bildirishnoma yuborish (agar test topshirgan odam o'qituvchining o'zi bo'lmasa)
    if not is_teacher(user.id):
        uname = f"@{user.username}" if user.username else "username yo'q"
        notify_text = (
            f"🔔 <b>Yangi test natijasi!</b>\n\n"
            f"👤 O'quvchi: <b>{user.full_name}</b> ({uname})\n"
            f"🆔 ID: <code>{user.id}</code>\n"
            f"📊 Natija: <b>{score}/{total}</b> ball ({percent}%)"
        )
        teacher_list = getattr(config, "TEACHER_IDS", [config.TEACHER_ID])
        for t_id in teacher_list:
            try:
                await bot.send_message(chat_id=t_id, text=notify_text, parse_mode="HTML")
            except Exception:
                pass


@dp.message(F.text == "ℹ️ Bot haqida")
async def about_bot(message: Message):
    await message.answer(
        "🤖 <b>Test Bot</b>\n\n"
        "Ushbu bot o'quvchilarga test topshirish, bilimlarini sinash va natijalarni avtomatik tekshirib olish imkoniyatini beradi.\n"
        "Barcha natijalar o'qituvchiga yetkaziladi.",
        parse_mode="HTML"
    )


# --- ASOSIY FUNKSIYA ---
async def main():
    print("Bot muvaffaqiyatli ishga tushirildi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
