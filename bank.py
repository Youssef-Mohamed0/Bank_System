import os
import re
import sqlite3
import gradio as gr

# ==============================
# Database Setup
# ==============================
DB_NAME = "bank_system.db"


def init_db():
    """إنشاء جدول الحسابات إذا لم يكن موجوداً"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            acc_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            balance REAL NOT NULL,
            pin TEXT NOT NULL,
            acc_type TEXT NOT NULL,
            extra_val REAL NOT NULL
        )
    """
    )
    conn.commit()
    conn.close()


init_db()


# ==============================
# Helper Validations
# ==============================
def is_valid_email(email):
    """التحقق من صحة صيغة البريد الإلكتروني"""
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email) is not None


# ==============================
# OOP Classes (with DB Persistence)
# ==============================
class BankAccount:

    def __init__(
        self, name, email, balance, pin, acc_type="Standard", extra_val=0.0
    ):
        self.name = name
        self.email = email
        self._balance = balance
        self.pin = str(pin)
        self.acc_type = acc_type
        self.extra_val = extra_val

    @property
    def balance(self):
        return self._balance

    def verify_pin(self, entered_pin):
        return str(entered_pin) == self.pin

    def deposit(self, amount):
        if amount <= 0:
            return False, "❌ deposit amount must be greater than 0."
        self._balance += amount
        return True, f"✅ ${amount:.2f} deposited successfully."

    def withdraw(self, amount):
        if amount <= 0:
            return False, "❌ withdrawal amount must be greater than 0."
        if amount > self._balance:
            return (
                False,
                f"❌ Insufficient balance. Current: ${self._balance:.2f}",
            )
        self._balance -= amount
        return True, f"✅ ${amount:.2f} withdrawn successfully."


class SavingsAccount(BankAccount):

    def __init__(self, name, email, balance, pin, interest_rate=0.05):
        super().__init__(
            name,
            email,
            balance,
            pin,
            acc_type="Savings Account",
            extra_val=interest_rate,
        )

    def add_interest(self):
        interest = self._balance * self.extra_val
        self._balance += interest
        return True, f"✅ Added ${interest:.2f} interest."


class CheckingAccount(BankAccount):

    def __init__(self, name, email, balance, pin, overdraft_limit=200.0):
        super().__init__(
            name,
            email,
            balance,
            pin,
            acc_type="Checking Account",
            extra_val=overdraft_limit,
        )

    def withdraw(self, amount):
        if amount <= 0:
            return False, "❌ Withdrawal amount must be greater than 0."
        if amount > self._balance + self.extra_val:
            return (
                False,
                f"❌ Exceeds overdraft limit (${self.extra_val:.2f}). Max drawable: ${self._balance + self.extra_val:.2f}",
            )
        self._balance -= amount
        return True, f"✅ ${amount:.2f} withdrawn successfully."


# ==============================
# Data Access Layer (DB Operations)
# ==============================
def get_account_by_id(acc_id):
    """جلب حساب من قاعدة البيانات ككائن OOP"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT acc_id, name, email, balance, pin, acc_type, extra_val FROM accounts WHERE acc_id = ?",
        (acc_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None, "❌ Account number not found."

    _, name, email, balance, pin, acc_type, extra_val = row

    if acc_type == "Savings Account":
        acc = SavingsAccount(name, email, balance, pin, extra_val)
    else:
        acc = CheckingAccount(name, email, balance, pin, extra_val)

    return acc, None


def update_account_balance(acc_id, new_balance):
    """تحديث الرصيد في قاعدة البيانات"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE accounts SET balance = ? WHERE acc_id = ?",
        (new_balance, acc_id),
    )
    conn.commit()
    conn.close()


# ==============================
# Gradio Controller Functions
# ==============================
def create_account(acc_type, name, email, balance, pin, extra_val):
    if not name or not email or not pin:
        return "❌ All fields are required."

    if not is_valid_email(email):
        return "❌ Invalid email address format."

    if len(str(pin)) < 4:
        return "❌ PIN must be at least 4 digits."

    if balance is None or balance < 0:
        return "❌ Initial balance cannot be negative."

    rate_or_limit = extra_val if extra_val is not None else 0.0

    if acc_type == "Savings Account":
        rate_or_limit = rate_or_limit / 100 if rate_or_limit > 1 else rate_or_limit

    # إدخال الحساب في قاعدة البيانات (يمنع تكرار الإيميل تلقائياً بفضل UNIQUE)
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO accounts (name, email, balance, pin, acc_type, extra_val)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (name, email, balance, str(pin), acc_type, rate_or_limit),
        )
        acc_id = cursor.lastrowid
        conn.commit()
        conn.close()
    except sqlite3.IntegrityError:
        return "❌ An account with this email already exists."

    return (
        f"✅ Account created successfully!\n"
        f"💳 Your Account ID is: {acc_id}\n"
        f"Name: {name} | Type: {acc_type} | Balance: ${balance:.2f}"
    )


def show_accounts():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT acc_id, name, email, balance, acc_type, extra_val FROM accounts"
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return [["-", "-", "-", "-", "-", "-"]]

    # تجهيز البيانات للعرض في جدول (تم إخفاء الـ PIN لسلامة الأمان)
    table_data = []
    for row in rows:
        acc_id, name, email, balance, acc_type, extra = row
        extra_label = (
            f"Rate: {extra*100}%"
            if acc_type == "Savings Account"
            else f"Limit: ${extra}"
        )
        table_data.append(
            [acc_id, name, email, f"${balance:.2f}", acc_type, extra_label]
        )

    return table_data


def handle_deposit(acc_num, pin, amount):
    acc, err = get_account_by_id(acc_num)
    if err:
        return err

    if not acc.verify_pin(pin):
        return "❌ Incorrect PIN."

    success, msg = acc.deposit(amount)
    if success:
        update_account_balance(acc_num, acc.balance)
        return f"{msg}\nNew Balance: ${acc.balance:.2f}"
    return msg


def handle_withdraw(acc_num, pin, amount):
    acc, err = get_account_by_id(acc_num)
    if err:
        return err

    if not acc.verify_pin(pin):
        return "❌ Incorrect PIN."

    success, msg = acc.withdraw(amount)
    if success:
        update_account_balance(acc_num, acc.balance)
        return f"{msg}\nNew Balance: ${acc.balance:.2f}"
    return msg


def handle_transfer(sender_id, sender_pin, receiver_id, amount):
    if sender_id == receiver_id:
        return "❌ Cannot transfer to the same account."

    if amount is None or amount <= 0:
        return "❌ Transfer amount must be greater than 0."

    sender, err1 = get_account_by_id(sender_id)
    if err1:
        return f"Sender Error: {err1}"

    if not sender.verify_pin(sender_pin):
        return "❌ Sender PIN is incorrect."

    receiver, err2 = get_account_by_id(receiver_id)
    if err2:
        return f"Receiver Error: {err2}"

    # تنفيذ السحب من المرسل والإيداع للمستلم
    success, msg = sender.withdraw(amount)
    if not success:
        return f"Transfer Failed: {msg}"

    receiver.deposit(amount)

    # حفظ الرصيد الجديد لكلا الحسابين في قاعدة البيانات
    update_account_balance(sender_id, sender.balance)
    update_account_balance(receiver_id, receiver.balance)

    return (
        f"✅ Transferred ${amount:.2f} successfully to {receiver.name} (Acc #{receiver_id}).\n"
        f"Your Remaining Balance: ${sender.balance:.2f}"
    )


# ==============================
# Gradio Interface
# ==============================
with gr.Blocks(title="Secure Bank System") as app:
    gr.Markdown("# 🏦 Secure Bank System (DB Persistence & Security)")

    with gr.Tab("Create Account"):
        acc_type = gr.Dropdown(
            choices=["Savings Account", "Checking Account"],
            value="Savings Account",
            label="Account Type",
        )
        name_input = gr.Textbox(label="Full Name")
        email_input = gr.Textbox(
            label="Email Address", placeholder="user@example.com"
        )
        pin_input = gr.Textbox(
            label="Security PIN",
            type="password",
            placeholder="Minimum 4 digits",
        )
        balance_input = gr.Number(label="Initial Balance ($)", value=100)
        extra_input = gr.Number(
            label="Interest Rate (%) / Overdraft Limit ($)",
            value=5,
            info="For Savings: Interest Rate %. For Checking: Overdraft Limit $",
        )

        create_btn = gr.Button("Create Account", variant="primary")
        create_out = gr.Textbox(label="Result")

        create_btn.click(
            create_account,
            inputs=[
                acc_type,
                name_input,
                email_input,
                balance_input,
                pin_input,
                extra_input,
            ],
            outputs=create_out,
        )

    with gr.Tab("Accounts Database"):
        show_btn = gr.Button("Refresh Accounts List")
        accounts_table = gr.Dataframe(
            headers=[
                "Acc ID",
                "Name",
                "Email",
                "Balance",
                "Account Type",
                "Details",
            ],
            datatype=["number", "str", "str", "str", "str", "str"],
            label="Registered Accounts",
        )
        show_btn.click(show_accounts, outputs=accounts_table)

    with gr.Tab("Transactions"):
        gr.Markdown("### Deposit / Withdraw")
        with gr.Row():
            acc_num = gr.Number(label="Account ID", precision=0)
            pin_check = gr.Textbox(label="PIN", type="password")
            amount = gr.Number(label="Amount ($)")

        with gr.Row():
            dep_btn = gr.Button("Deposit")
            with_btn = gr.Button("Withdraw")

        trans_out = gr.Textbox(label="Transaction Result")

        dep_btn.click(
            handle_deposit,
            inputs=[acc_num, pin_check, amount],
            outputs=trans_out,
        )
        with_btn.click(
            handle_withdraw,
            inputs=[acc_num, pin_check, amount],
            outputs=trans_out,
        )

    with gr.Tab("Transfer Money"):
        gr.Markdown("### Transfer Between Accounts")
        with gr.Row():
            s_id = gr.Number(label="Sender Account ID", precision=0)
            s_pin = gr.Textbox(label="Sender PIN", type="password")

        with gr.Row():
            r_id = gr.Number(label="Receiver Account ID", precision=0)
            t_amount = gr.Number(label="Transfer Amount ($)")

        transfer_btn = gr.Button("Execute Transfer", variant="primary")
        transfer_out = gr.Textbox(label="Transfer Status")

        transfer_btn.click(
            handle_transfer,
            inputs=[s_id, s_pin, r_id, t_amount],
            outputs=transfer_out,
        )

app.launch()