# Voucher Purchase API

A FastAPI-based RESTful API for purchasing vouchers with Paystack payment integration. The application allows users to register, login, and purchase vouchers of predefined amounts (2, 5, 10, 20, 50 cedis).

## Features

- User registration and authentication using JWT
- Voucher purchase with Paystack payment gateway integration
- PostgreSQL database with SQLAlchemy ORM
- Structured architecture (routers, controllers, schemas, models)
- Input validation using Pydantic
- Protected endpoints with authentication

## Prerequisites

- Python 3.8+
- PostgreSQL
- Paystack account for payment integration

## Installation

1. Clone the repository:
```bash
git clone https://github.com/andrewantwi/Voucher-Purchase-System.git
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate
```
3. Install dependencies:
```bash
pip install -r requirements.txt
```
4. Set up PostgreSQL database:

5. Configure environment variables: Create a .env file in the root directory with:
```bash
DATABASE_URL=postgresql://username:password@localhost:5432/voucher_db
SECRET_KEY=your-secret-key-here
PAYSTACK_SECRET_KEY=sk_test_your_paystack_secret_key
```

