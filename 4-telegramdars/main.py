import os

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, \
    LabeledPrice
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext, Filters, ConversationHandler, \
    CallbackQueryHandler, PreCheckoutQueryHandler
import db

TOKEN = "8708071841:AAEr78uOHJ4tnY69Av7BBaXN0wvlxmtAldo"
PROVIDER_TOKEN = "398062629:TEST:999999999_F91D8F69C042267444B74CC0B3C747757EB0E065"
ADMIN_PASSWORD = "123"
ADMIN = set()

(NAME, PHONE, LOCATION, MAIN_MENU, EDIT_NAME, EDIT_PHONE, SETTINGS_MENU, FOOD_MENU) = range(8)
(ADMIN_MENU, ADD_CATEGORY, ADD_PRODUCT_CAT, ADD_PRODUCT_NAME,
 ADD_PRODUCT_PRICE, ADD_PRODUCT_DESC, ADD_PRODUCT_IMAGE) = range(8, 15)


def start(update: Update, context: CallbackContext):
    user = db.get_user(update.effective_user.id)

    if user:
        return main_menu(update, context)

    update.message.reply_text("Assalomu Alaykum\n\n"
                              "Ism Familya kiriting: ")
    return NAME


def get_name(update, context):
    context.user_data['name'] = update.message.text
    update.message.reply_text("Telefon raqamingizni kiriting: ",
                              reply_markup=ReplyKeyboardMarkup(
                                  [[KeyboardButton("Raqam yuborish", request_contact=True)]],
                                  resize_keyboard=True
                              ))
    return PHONE


def get_phone(update, context):
    context.user_data['phone'] = update.message.contact.phone_number
    update.message.reply_text("Joylashuv manzilingizni kiriting: ",
                              reply_markup=ReplyKeyboardMarkup(
                                  [[KeyboardButton("Joylashuvni yuborish", request_location=True)]],
                                  resize_keyboard=True
                              ))
    return LOCATION


def get_location(update, context):
    loc = update.message.location

    db.add_user(
        update.effective_user.id,
        context.user_data['name'],
        context.user_data['phone'],
        loc.latitude,
        loc.longitude
    )

    update.message.reply_text("Ro'yhatdan o'tdingiz !")
    return main_menu(update, context)


def main_menu(update, context):
    update.message.reply_text(
        "Asosiy menu: ",
        reply_markup=ReplyKeyboardMarkup(
            [
                ["📋 Menyu", "🛒 Savat"],
                ["⚙️ Sozlamalar"],
                ["✍ Izoh qoldirish"],
            ],
            resize_keyboard=True
        )
    )
    return MAIN_MENU


def main_menu_select(update, context):
    text = update.message.text

    if text == "🛒 Savat":
        return show_cart(update, context)

    if text == "📋 Menyu":
        return food_menu(update, context)

    if text == "⚙️ Sozlamalar":
        return settings_menu(update, context)

    if text == "✍ Izoh qoldirish":
        update.message.reply_text("Izoh qismini dasturchi bo'sh bo'sa qiladi !")
        return MAIN_MENU


def show_cart(update, context):
    cart = context.user_data.get("cart")

    if not cart:
        update.message.reply_text("Savat bo'sh")
        return MAIN_MENU

    text = "Savatingiz\n\n"
    total = 0

    for item in cart:
        summa = item['price'] * item['qty']
        total += summa
        text += f"{item['name']} x {item['qty']} = {summa} so'm\n\n"
    text += f"Jami: {total} so'm"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Buyurtma berish",
                callback_data="checkout"
            ),
            InlineKeyboardButton(
                "❌ Bekor qilish",
                callback_data="clear_cart"
            ),
        ]
    ])
    update.message.reply_text(text, reply_markup=keyboard)
    return MAIN_MENU


def food_menu(update, context):
    cats = db.get_categories()

    keyboard = [[c[1] for c in cats]]
    keyboard.append(['⬅️ Orqaga'])

    update.message.reply_text(
        "Menyulardan birin tanlang: ",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return FOOD_MENU


def food_menu_select(update, context):
    text = update.message.text

    if text == "⬅️ Orqaga":
        return main_menu(update, context)

    cat_cod = db.get_categories_code_by_name(text)
    if not cat_cod:
        update.message.reply_text("Category topilmadi")
        return FOOD_MENU

    product = db.get_product_by_category(cat_cod)

    if not product:
        update.message.reply_text("Bu category mahulot yo'q")
        return FOOD_MENU

    keyboard = [
        [InlineKeyboardButton(p[1], callback_data=f"product_{p[0]}")]
        for p in product
    ]
    update.message.reply_text(f"{text} mahuloatlari: ",
                              reply_markup=InlineKeyboardMarkup(keyboard))
    return FOOD_MENU


def settings_menu(update, context):
    update.message.reply_text("Ma'lumotlarni tahrirlash: ",
                              reply_markup=ReplyKeyboardMarkup(
                                  [
                                      ['Ism familya'],
                                      ['Telefon raqam'],
                                      ["⬅️ Orqaga"]
                                  ],
                                  resize_keyboard=True
                              ))
    return SETTINGS_MENU


def settings_select(update, context):
    text = update.message.text

    if text == "Ism familya":
        update.message.reply_text("Yangi ism familya kiriitng: ")
        return EDIT_NAME

    if text == "Telefon raqam":
        update.message.reply_text("Yangi telefon raqam uboring: ", reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("Raqa yuborish", request_contact=True)]], resize_keyboard=True
        ))
        return EDIT_PHONE

    if text == "⬅️ Orqaga":
        return main_menu(update, context)


def edit_name(update, context):
    db.update_name(update.effective_user.id, update.message.text)
    update.message.reply_text("Ism familya o'zgaririldi !")
    return main_menu(update, context)


def edit_phone(update, context):
    db.update_name(update.effective_user.id, update.message.contact.phone_number)
    update.message.reply_text("Teleon raqam o'zgaririldi !")
    return main_menu(update, context)


def product_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    ol_msg_id = context.user_data.get("product_message_id")
    if ol_msg_id:
        try:
            context.bot.delete_message(
                chat_id=query.message.chat_id,
                message_id=ol_msg_id,
            )
        except:
            pass

    product_id = int(query.data.split("_")[1])
    product = db.get_products(product_id)

    context.user_data['current_product'] = {
        "id": product[0],
        "name": product[1],
        "price": product[2],
        "desc": product[3],
        "image": product[4],
    }
    context.user_data['qty'] = 1

    msg = query.message.reply_photo(
        photo=open(product[4], "rb"),
        caption=(
            f"{product[1]}\n\n"
            f"Narxi: {product[2]} so'm\n"
            f"Miqdori: 1\n\n"
            f"{product[3]}"
        ),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➖", callback_data="qty_plus"),
                InlineKeyboardButton("1", callback_data="noop"),
                InlineKeyboardButton("➕", callback_data="qty_minus"),
            ],
            [
                InlineKeyboardButton(
                    "🛒 Savatga qo'shish",
                    callback_data="add_to_cart"
                )
            ]
        ])
    )
    context.user_data['product_message_id'] = msg.message_id


def send_product_card_first(query, context):
    product = context.user_data['current_product']
    qty = context.user_data['qty']

    keyboard = [
        [
            InlineKeyboardButton("➖", callback_data="qty_plus"),
            InlineKeyboardButton(str(qty), callback_data="noop"),
            InlineKeyboardButton("➕", callback_data="qty_minus"),
        ],
        [
            InlineKeyboardButton(
                "🛒 Savatga qo'shish",
                callback_data="add_to_cart"
            )
        ]
    ]

    caption = (
        f"{product['name']}\n\n"
        f"Narxi: {product['price']} so'm\n"
        f"Miqdori: {qty}\n\n"
        f"{product['desc']}"
    ),

    query.message.reply_photo(
        photo=open("images.jpg", "rb"),
        caption=caption,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def send_product_card_update(query, context):
    if not query.message.photo:
        return

    product = context.user_data.get("current_product")
    qty = context.user_data.get("qty", 1)

    if not product:
        return

    keyboard = [
        [
            InlineKeyboardButton("➖", callback_data="qty_plus"),
            InlineKeyboardButton(str(qty), callback_data="noop"),
            InlineKeyboardButton("➕", callback_data="qty_minus"),
        ],
        [
            InlineKeyboardButton(
                "🛒 Savatga qo'shish",
                callback_data="add_to_cart"
            )
        ]
    ]

    caption = (
        f"{product['name']}\n\n"
        f"Narxi: {product['price']} so'm\n"
        f"Miqdori: {qty}\n\n"
        f"{product['desc']}"
    ),

    query.edit_message_caption(
        caption=caption,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def cart_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    if not query.message.photo:
        return

    product = context.user_data.get("current_product")
    if not product:
        return

    qty = context.user_data.get("qty", 1)

    if query.data == "qty_plus":
        qty += 1

    elif query.data == "qty_minus":
        if qty > 1:
            qty -= 1

    elif query.data == "add_to_cart":
        context.user_data.setdefault("cart", []).append({
            "id": product['id'],
            "name": product['name'],
            "price": product['price'],
            "qty": qty,
        })
        query.message.reply_text("Mqahsulot savatga qo'shildi !")
        return

    context.user_data['qty'] = qty

    keyboard = [
        [
            InlineKeyboardButton("➖", callback_data="qty_minus"),
            InlineKeyboardButton(str(qty), callback_data="noop"),
            InlineKeyboardButton("➕", callback_data="qty_plus"),
        ],
        [
            InlineKeyboardButton(
                "Savatga qo'shish",
                callback_data="add_to_cart"
            )
        ]
    ]

    query.edit_message_caption(
        caption=(
            f"{product['name']}\n\n"
            f"Narxi: {product['price']} so'm\n"
            f"Miqdori: {qty}\n\n"
            f"{product['desc']}"
        ),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def order_callback(update, context):
    query = update.callback_query
    query.answer()

    if query.data == "order_confirm":
        cart = context.user_data.get("cart", [])

        if not cart:
            query.message.reply_text("Svating bo'sh shoptoli 🤷‍♂️")
            return
        prices = []
        total = 0

        for item in cart:
            amount = item['price'] * item['qty']
            total += amount
            prices.append(
                LabeledPrice(
                    label=f"{item['name']} x {item['qty']}",
                    amount=amount * 100
                )
            )

        context.bot.send_invoice(
            chat_id=query.message.chat_id,
            title="Buyurtma uchun to'lov 💸",
            description="Buyutmangiz uchun to'liovni dacom ettiring ➡️",
            payload="order_payment_payload",
            provider_token=PROVIDER_TOKEN,
            currency="UZS",
            prices=prices,
            start_parameter='food_order',
        )

    elif query.data == "order_cancel":
        context.user_data['cart'] = []
        query.message.delete()
        query.message.chat.send_message("Buyurtma bekor qilindi ❌")


def precheckout_callback(update, context):
    update.pre_checkout_query.answer(ok=True)


def successful_payment_callback(update: Update, context: CallbackContext):
    context.user_data['cart'] = []

    update.message.reply_text(
        "✅ To'lov muvofaqiyatli amalga oshirlidi\n"
        "📦 Buyurtmangiz qabul qilindi."
    )


def admin_login(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("Parol kiritng: /admin <password>")
        return

    if context.args[0] == ADMIN_PASSWORD:
        ADMIN.add(update.effective_user.id)
        update.message.reply_text(
            "Admin pamnelga kirdingiz",
            reply_markup=ReplyKeyboardMarkup(
                [
                    ["Category qo'shish"],
                    ["Mahsulot qo'shish"],
                ],
                resize_keyboard=True
            )
        )
        return ADMIN_MENU
    else:
        update.message.reply_text("Notog'ri parol !")


def admin_menu(update: Update, context: CallbackContext):
    text = update.message.text

    if update.effective_user.id not in ADMIN:
        update.message.reply_text("Ruhsat yo'q !")
        return MAIN_MENU

    if text == "Category qo'shish":
        update.message.reply_text("Catgeory nomini kiriting: ")
        return ADD_CATEGORY

    if text == "Mahsulot qo'shish":
        update.message.reply_text("Mahulot o'shihs qismi: ")
        return ADD_PRODUCT_CAT

    if text == "⬅️ Orqaga":
        ADMIN.discard(update.effective_user.id)
        update.message.reply_text("Admin paneldan chiqdingiz !")
        return ConversationHandler.END


def add_category(update: Update, context: CallbackContext):
    name = update.message.text
    code = name.lower().replace(" ", "_")

    db.add_category(name, code)

    update.message.reply_text(f"Category qo'shildi: {name}\n\nCategory code: {code}")
    return ADMIN_MENU


def add_product_cat(update: Update, context: CallbackContext):
    code = update.message.text

    if not db.category_exists(code):
        update.message.reply_text("Bunday catgeorey yo'q, codeni tekshiring.")
        return ADD_PRODUCT_CAT

    context.user_data['cat'] = code
    update.message.reply_text("Mahsulot nomini kiriting: ")
    return ADD_PRODUCT_NAME


def add_product_name(update, context):
    context.user_data['name'] = update.message.text
    update.message.reply_text("Narxini kiitng: ")
    return ADD_PRODUCT_PRICE


def add_product_price(update, context):
    if not update.message.text.isdigit():
        update.message.reply_text("Narxini faqat raqam bo'lsin !")
        return ADD_PRODUCT_PRICE

    context.user_data['price'] = int(update.message.text)
    update.message.reply_text("Tavsif kiriitng: ")
    return ADD_PRODUCT_DESC


def add_product_desc(update, context):
    context.user_data['desc'] = update.message.text
    update.message.reply_text("Mahulot rasmini yuboring: ")
    return ADD_PRODUCT_IMAGE


def add_product_image(update, context):
    photo = update.message.photo[-1]
    file = photo.get_file()

    os.makedirs("images", exist_ok=True)

    safe_name = context.user_data['name'].replace(" ", "_")
    image_path = f"images/{safe_name}.jpg"

    file.download(image_path)

    d = context.user_data
    db.add_product(
        d['cat'],
        d['name'],
        d['price'],
        d['desc'],
        image_path
    )

    update.message.reply_text("Mahulot qo'shildi !")
    return ADMIN_MENU


def main():
    db.create_table()

    updater = Updater(TOKEN)
    dp = updater.dispatcher

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start),
                      CommandHandler("admin", admin_login)],
        states={
            NAME: [MessageHandler(Filters.text, get_name)],
            PHONE: [MessageHandler(Filters.contact, get_phone)],
            LOCATION: [MessageHandler(Filters.location, get_location)],

            MAIN_MENU: [MessageHandler(Filters.text, main_menu_select)],
            SETTINGS_MENU: [MessageHandler(Filters.text, settings_select)],
            FOOD_MENU: [MessageHandler(Filters.text, food_menu_select)],

            ADMIN_MENU: [MessageHandler(Filters.text, admin_menu)],
            ADD_CATEGORY: [MessageHandler(Filters.text, add_category)],
            ADD_PRODUCT_CAT: [MessageHandler(Filters.text, add_product_cat)],
            ADD_PRODUCT_NAME: [MessageHandler(Filters.text, add_product_name)],
            ADD_PRODUCT_PRICE: [MessageHandler(Filters.text, add_product_price)],
            ADD_PRODUCT_DESC: [MessageHandler(Filters.text, add_product_desc)],
            ADD_PRODUCT_IMAGE: [MessageHandler(Filters.photo, add_product_image)],

            EDIT_NAME: [MessageHandler(Filters.text, edit_name)],
            EDIT_PHONE: [MessageHandler(Filters.contact, edit_phone)],
        },
        fallbacks=[],
    )

    dp.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern="^noop$"))
    dp.add_handler(CallbackQueryHandler(product_callback, pattern="^product_"))
    dp.add_handler(CallbackQueryHandler(cart_callback, pattern="^(qty_|add_to_cart)"))
    dp.add_handler(CallbackQueryHandler(order_callback, pattern="^order_"))

    dp.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    dp.add_handler(MessageHandler(Filters.successful_payment, successful_payment_callback))

    dp.add_handler(conv)
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
