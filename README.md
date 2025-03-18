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
