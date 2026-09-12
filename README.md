# 🏦 Secure Banking System

A lightweight, secure, and interactive Banking Application built with **Python**, **Object-Oriented Programming (OOP)**, **SQLite**, and **Gradio UI**.

---

## Features

* **OOP Architecture:** Built using key Object-Oriented principles, including **Inheritance** (`SavingsAccount`, `CheckingAccount`), **Encapsulation**, and **Method Overriding**.
* **Account Types:**
  * 💰 **Savings Account:** Earns interest over time.
  * 💳 **Checking Account:** Supports overdraft protection with customizable limits.
* **Security & Validation:**
  * Email format validation and unique email constraints.
  * PIN-protected transactions (Deposit, Withdraw, Transfer).
* **Data Persistence:** Integrated with **SQLite** to ensure user data and balances are saved permanently.
* **Interactive UI:** Clean web interface built using **Gradio**, featuring dynamic dataframes for account browsing.

---

### Prerequisites
```bash
pip install gradio
