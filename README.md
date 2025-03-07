# Voucher Purchase System

## Instructions

1. Clone the repository:
    ```sh
    git clone <repository-url>
    ```

2. Change into the cloned repository directory:
    ```sh
    cd <repository-directory>
    ```

3. Create a virtual environment:
    ```sh
    python -m venv venv
    ```

4. Activate the virtual environment:
    ```sh
    source venv/bin/activate
    ```

5. Install the required packages:
    ```sh
    pip install -r requirements.txt
    ```

6. Migrate the database:
    ```sh
    alembic upgrade head
    ```

7. Run the application:
    ```sh
    uvicorn main:app
    ```