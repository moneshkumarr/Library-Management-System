import cx_Oracle
from datetime import datetime, timedelta
import os
import platform
import sys
from typing import Optional, List, Tuple, Any
def get_connection() -> Optional[cx_Oracle.Connection]:
    """Establish a connection to the Oracle database."""
    try:
        dsn = cx_Oracle.makedsn("10.1.67.153", 1522, service_name="orclNEW")
        connection = cx_Oracle.connect(user='msc23pt09', password='msc23pt09', dsn=dsn)
        return connection
    except cx_Oracle.Error as err:
        print(f"Database connection error: {err}")
        return None

# Utility Functions
def clear_screen() -> None:
    """Clear the terminal screen based on the operating system."""
    os.system("cls" if platform.system() == "Windows" else "clear")

def get_valid_date(prompt: str) -> Optional[datetime.date]:
    """Get a valid date input from the user in YYYY-MM-DD format."""
    while True:
        try:
            date_str = input(prompt).strip()
            if not date_str:
                return None
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD or leave blank.")

def get_valid_number(prompt: str, num_type: type = float, allow_empty: bool = False) -> Any:
    """Get a valid numeric input from the user."""
    while True:
        try:
            value = input(prompt).strip()
            if allow_empty and not value:
                return None
            return num_type(value)
        except ValueError:
            print(f"Invalid input. Please enter a valid {num_type.__name__}{' or leave blank' if allow_empty else ''}.")

def handle_database_errors(func):
    """Decorator to handle common database errors."""
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        except cx_Oracle.DatabaseError as err:
            error_obj, = err.args
            error_messages = {
                1: "Error: That record already exists.",
                2291: "Error: Related record not found.",
                2292: "Error: Cannot delete - related records exist."
            }
            print(error_messages.get(error_obj.code, f"Database Error: {err}"))
            print(f"Help: https://docs.oracle.com/error-help/db/ora-{error_obj.code:05d}/")
            return None
        except Exception as err:
            print(f"Unexpected Error: {err}")
            return None
    return wrapper

# Audit Logging Function
@handle_database_errors
def log_action(action_type: str, user_id: str, details: str) -> None:
    """Log an action to the audit log table."""
    with get_connection() as cnx:
        if cnx is None:
            return
        with cnx.cursor() as cursor:
            cursor.callproc("LogAudit", [action_type, user_id, details])

# View Audit History
@handle_database_errors
def view_audit_history() -> None:
    """Display the audit log history."""
    with get_connection() as cnx:
        if cnx is None:
            return
        with cnx.cursor() as cursor:
            print("\n--- Audit Log History ---")
            cursor.execute("""
                SELECT ACTION_ID, ACTION_TYPE, USER_ID, ACTION_TIMESTAMP, ACTION_DETAILS 
                FROM AUDIT_LOG 
                ORDER BY ACTION_TIMESTAMP DESC
            """)
            results = cursor.fetchall()

            if not results:
                print("No audit records found.")
                return

            print("\nAudit History:")
            print("=" * 120)
            print(f"{'ID':<5}{'Action Type':<20}{'User ID':<15}{'Timestamp':<30}{'Details':<50}")
            print("-" * 120)

            for row in results:
                action_id, action_type, user_id, timestamp, details = row
                print(f"{action_id:<5}{action_type:<20}{user_id:<15}{timestamp:<30}{details:<50}")

            print("=" * 120)

# User Management
@handle_database_errors
def insert_user() -> None:
    """Insert a new user into the database."""
    with get_connection() as cnx:
        if cnx is None:
            return
        with cnx.cursor() as cursor:
            print("\n--- Add New Member ---")
            user_id = input("Enter User ID performing action: ").strip()
            mno = input("Enter Member Code: ").strip()
            if not mno:
                print("Member Code cannot be empty!")
                return
                
            mname = input("Enter Member Name: ").strip()
            if not mname:
                print("Member Name cannot be empty!")
                return
                
            dom_date = get_valid_date("Enter Date of Membership (YYYY-MM-DD): ")
            if not dom_date:
                print("Date of Membership cannot be empty!")
                return
            addr = input("Enter Address: ").strip()
            mob = input("Enter Mobile Number: ").strip()
            if not mob:
                print("Mobile Number cannot be empty!")
                return

            cursor.callproc("InsertUser", [mno, mname, dom_date, addr, mob])
            cnx.commit()
            print("Member added successfully!")
            log_action("INSERT_USER", user_id, f"Added member {mno} - {mname}")

@handle_database_errors
def update_user() -> None:
    """Update an existing user's information."""
    with get_connection() as cnx:
        if cnx is None:
            return
        with cnx.cursor() as cursor:
            print("\n--- Update Member ---")
            user_id = input("Enter User ID performing action: ").strip()
            mno = input("Enter Member Code to update: ").strip()
            if not mno:
                print("Member Code cannot be empty!")
                return

            cursor.execute(
                "SELECT MNAME, DOM, ADDR, MOB FROM Users WHERE MNO = :mno",
                {'mno': mno}
            )
            current = cursor.fetchone()
            if not current:
                print("Member not found!")
                return

            mname = input(f"Enter New Member Name (current: {current[0]}): ").strip() or current[0]
            change_dom = input("Change Date of Membership? (y/n): ").lower() == 'y'
            dom_date = get_valid_date("Enter New Date of Membership (YYYY-MM-DD): ") if change_dom else current[1]
            addr = input(f"Enter New Address (current: {current[2]}): ").strip() or current[2]
            mob = input(f"Enter New Mobile Number (current: {current[3]}): ").strip() or current[3]

            cursor.callproc("UpdateUser", [mno, mname, dom_date, addr, mob])
            cnx.commit()
            print("Member updated successfully!")
            log_action("UPDATE_USER", user_id, f"Updated member {mno} - {mname}")

@handle_database_errors
def delete_user() -> None:
    """Delete a user from the database."""
    with get_connection() as cnx:
        if cnx is None:
            return
        with cnx.cursor() as cursor:
            print("\n--- Delete Member ---")
            user_id = input("Enter User ID performing action: ").strip()
            mno = input("Enter Member Code to delete: ").strip()
            if not mno:
                print("Member Code cannot be empty!")
                return

            confirm = input(f"Are you sure you want to delete member {mno}? (y/n): ").lower()
            if confirm != 'y':
                print("Deletion cancelled.")
                return

            cursor.callproc("DeleteUser", [mno])
            cnx.commit()
            print("Member deleted successfully!")
            log_action("DELETE_USER", user_id, f"Deleted member {mno}")

@handle_database_errors
def search_user() -> None:
    """Search for a user in the database by member code or name."""
    with get_connection() as cnx:
        if cnx is None:
            return
        with cnx.cursor() as cursor:
            print("\n--- Search Member ---")
            search_term = input("Enter Member Code or Name to search: ").strip()
            if not search_term:
                print("Search term cannot be empty!")
                return

            ref_cursor = cursor.var(cx_Oracle.CURSOR)
            cursor.callproc("SearchUser", [search_term, ref_cursor])
            results = ref_cursor.getvalue().fetchall()

            if results:
                print("\nSearch Results:")
                print("-" * 80)
                for row in results:
                    print(f"Code: {row[0]}, Name: {row[1]}, Join Date: {row[2]}")
                    print(f"Address: {row[3]}, Mobile: {row[4]}")
                    print("-" * 80)
            else:
                print("No matching members found.")

# Catalog Management
@handle_database_errors
def insert_book() -> None:
    """Insert a new book into the catalog."""
    with get_connection() as cnx:
        if cnx is None:
            return
        with cnx.cursor() as cursor:
            print("\n--- Add New Book ---")
            user_id = input("Enter User ID performing action: ").strip()
            bno = input("Enter Book Code: ").strip()
            if not bno:
                print("Book Code cannot be empty!")
                return
                
            bname = input("Enter Book Title: ").strip()
            if not bname:
                print("Book Title cannot be empty!")
                return
                
            auth = input("Enter Author: ").strip()
            if not auth:
                print("Author cannot be empty!")
                return
            price = get_valid_number("Enter Price: ", float)
            if price is None or price < 0:
                print("Price must be a positive number!")
                return
                
            publ = input("Enter Publisher: ").strip()
            if not publ:
                print("Publisher cannot be empty!")
                return

            cursor.callproc("InsertBook", [bno, bname, auth, price, publ])
            cnx.commit()
            print("Book added successfully!")
            log_action("INSERT_BOOK", user_id, f"Added book {bno} - {bname}")

@handle_database_errors
def update_book() -> None:
    """Update an existing book's information."""
    with get_connection() as cnx:
        if cnx is None:
            return
        with cnx.cursor() as cursor:
            print("\n--- Update Book ---")
            user_id = input("Enter User ID performing action: ").strip()
            bno = input("Enter Book Code to update: ").strip()
            if not bno:
                print("Book Code cannot be empty!")
                return

            cursor.execute(
                "SELECT BNAME, AUTHOR, PRICE, PUBL FROM BookRecord WHERE BNO = :bno",
                {'bno': bno}
            )
            current = cursor.fetchone()
            if not current:
                print("Book not found!")
                return

            print("\nCurrent Book Details:")
            print(f"1. Title: {current[0]}")
            print(f"2. Author: {current[1]}")
            print(f"3. Price: {current[2]}")
            print(f"4. Publisher: {current[3]}")

            fields = input("\nEnter numbers of fields to update (e.g., '1,3'): ").split(',')
            bname = current[0] if '1' not in fields else input("Enter New Title: ").strip() or current[0]
            auth = current[1] if '2' not in fields else input("Enter New Author: ").strip() or current[1]
            price = current[2] if '3' not in fields else get_valid_number("Enter New Price: ", float) or current[2]
            publ = current[3] if '4' not in fields else input("Enter New Publisher: ").strip() or current[3]

            cursor.callproc("UpdateBook", [bno, bname, auth, price, publ])
            cnx.commit()
            print("Book updated successfully!")
            log_action("UPDATE_BOOK", user_id, f"Updated book {bno} - {bname}")

@handle_database_errors
def delete_book() -> None:
    """Delete a book from the catalog."""
    with get_connection() as cnx:
        if cnx is None:
            return
        with cnx.cursor() as cursor:
            print("\n--- Delete Book ---")
            user_id = input("Enter User ID performing action: ").strip()
            bno = input("Enter Book Code to delete: ").strip()
            if not bno:
                print("Book Code cannot be empty!")
                return

            cursor.execute("SELECT BNAME FROM BookRecord WHERE BNO = :bno", {'bno': bno})
            book = cursor.fetchone()
            if not book:
                print("Book not found!")
                return

            confirm = input(f"Are you sure you want to delete '{book[0]}'? (y/n): ").lower()
            if confirm != 'y':
                print("Deletion cancelled.")
                return

            cursor.callproc("DeleteBook", [bno])
            cnx.commit()
            print("Book deleted successfully!")
            log_action("DELETE_BOOK", user_id, f"Deleted book {bno} - {book[0]}")

@handle_database_errors
def search_book() -> None:
    """Search for books in the catalog."""
    with get_connection() as cnx:
        if cnx is None:
            return
        with cnx.cursor() as cursor:
            print("\n--- Search Books ---")
            search_term = input("Enter Book Code, Title, or Author to search: ").strip()
            if not search_term:
                print("Search term cannot be empty!")
                return

            ref_cursor = cursor.var(cx_Oracle.CURSOR)
            cursor.callproc("SearchBook", [search_term, ref_cursor])
            results = ref_cursor.getvalue().fetchall()

            if results:
                print("\nSearch Results:")
                print("=" * 90)
                print(f"{'Code':<10}{'Title':<30}{'Author':<25}{'Price':<10}{'Publisher':<15}")
                print("-" * 90)
                for row in results:
                    print(f"{row[0]:<10}{row[1]:<30}{row[2]:<25}{row[3]:<10.2f}{row[4]:<15}")
                print("=" * 90)
            else:
                print("No matching books found.")

# Fine Management
@handle_database_errors
def calculate_fine_for_member(mno: str) -> float:
    """Calculate fines for overdue books for a member."""
    with get_connection() as cnx:
        if cnx is None:
            return 0.0
        with cnx.cursor() as cursor:
            print(f"\n--- Calculating Fines for Member {mno} ---")
            cursor.execute("SELECT MNAME FROM Users WHERE MNO = :mno", {'mno': mno})
            member = cursor.fetchone()
            if not member:
                print("Member not found!")
                return 0.0

            print(f"Member: {member[0]}")
            ref_cursor = cursor.var(cx_Oracle.CURSOR)
            cursor.callproc("CalculateMemberFines", [mno, ref_cursor])
            overdue_books = ref_cursor.getvalue().fetchall()

            if not overdue_books:
                print("No outstanding fines for this member.")
                return 0.0

            total_fine = 0.0
            print("\nOverdue Books:")
            print("=" * 120)
            print(f"{'Book ID':<10}{'Title':<25}{'Due Date':<15}{'Return Date':<15}{'Fine':<15}")
            print("-" * 120)

            for book in overdue_books:
                bno, bname, due_date, actual_return, fine_amount = book
                total_fine += fine_amount
                print(f"{bno:<10}{bname:<25}{due_date.strftime('%Y-%m-%d'):<15}"
                      f"{actual_return.strftime('%Y-%m-%d') if actual_return else 'Not Returned':<15}"
                      f"₹{fine_amount:.2f}")

            print("=" * 120)
            print(f"Total Fine Due: ₹{total_fine:.2f}")
            return total_fine

@handle_database_errors
def pay_fine(mno: str) -> None:
    """Process payment for a member's fines."""
    total_fine = calculate_fine_for_member(mno)
    if total_fine <= 0:
        return

    with get_connection() as cnx:
        if cnx is None:
            return
        with cnx.cursor() as cursor:
            print("\n--- Payment Processing ---")
            user_id = input("Enter User ID performing action: ").strip()
            print(f"Total Amount Due: ₹{total_fine:.2f}")
            
            amount_paid = get_valid_number(f"Enter amount to pay (max ₹{total_fine:.2f}): ", float)
            if amount_paid is None or amount_paid <= 0:
                print("Invalid payment amount!")
                return
                
            if amount_paid > total_fine:
                print("Payment amount exceeds total due. Adjusting to total due.")
                amount_paid = total_fine

            payment_method = input("Enter payment method (Cash/Card/Online): ").strip()
            if not payment_method:
                print("Payment method cannot be empty!")
                return

            cursor.callproc("PayMemberFines", [mno, payment_method])
            cnx.commit()
            print(f"Payment of ₹{amount_paid:.2f} recorded successfully!")
            log_action("PAY_FINE", user_id, f"Paid fine for member {mno}, amount: ₹{amount_paid:.2f}")
            if amount_paid < total_fine:
                print(f"Remaining balance: ₹{(total_fine - amount_paid):.2f}")

@handle_database_errors
def view_fine_history(mno: str) -> None:
    """View a member's fine payment history."""
    with get_connection() as cnx:
        if cnx is None:
            return
        with cnx.cursor() as cursor:
            print(f"\n--- Fine History for Member {mno} ---")
            cursor.execute("SELECT MNAME FROM Users WHERE MNO = :mno", {'mno': mno})
            member = cursor.fetchone()
            if not member:
                print("Member not found!")
                return

            print(f"Member: {member[0]}\n")
            query = """
            SELECT f.FINE_ID, b.BNAME, 
                   TO_CHAR(r.DUE_DATE, 'YYYY-MM-DD') as DUE_DATE,
                   TO_CHAR(f.FINE_DATE, 'YYYY-MM-DD') as FINE_DATE,
                   f.FINE_AMOUNT,
                   CASE WHEN f.PAID_STATUS = 'Y' 
                        THEN 'Paid on ' || TO_CHAR(f.PAYMENT_DATE, 'YYYY-MM-DD') 
                        ELSE 'Unpaid' END as PAYMENT_STATUS,
                   f.PAYMENT_METHOD
            FROM Fines f
            JOIN Issue i ON f.ISSUE_ID = i.ISSUE_ID
            JOIN BookRecord b ON i.BNO = b.BNO
            JOIN Return r ON i.ISSUE_ID = r.ISSUE_ID
            WHERE i.MNO = :mno
            ORDER BY f.FINE_DATE DESC
            """
            cursor.execute(query, {'mno': mno})
            fines = cursor.fetchall()

            if not fines:
                print("No fine history found for this member.")
                return

            print("\nFine History:")
            print("=" * 120)
            print(f"{'ID':<8}{'Book':<25}{'Due Date':<12}{'Fine Date':<12}"
                  f"{'Amount':<12}{'Status':<20}{'Method':<15}")
            print("-" * 120)

            total_fined = 0.0
            for fine in fines:
                fine_id, bname, due_date, fine_date, amount, status, method = fine
                method = method or 'N/A'
                print(f"{fine_id:<8}{bname:<25}{due_date:<12}{fine_date:<12}"
                      f"₹{amount:<11.2f}{status:<20}{method:<15}")
                total_fined += amount

            print("=" * 120)
            print(f"Total Fined: ₹{total_fined:.2f}")

# Reporting Functions
@handle_database_errors
def most_popular_books() -> None:
    """Display the most frequently borrowed books."""
    with get_connection() as cnx:
        if cnx is None:
            return
        with cnx.cursor() as cursor:
            print("\n--- Most Popular Books ---")
            limit = get_valid_number("Enter number of top books to display (default 10): ", int, True) or 10
            if limit <= 0:
                print("Limit must be positive!")
                return

            ref_cursor = cursor.var(cx_Oracle.CURSOR)
            cursor.callproc("MostPopularBooks", [ref_cursor])
            results = ref_cursor.getvalue().fetchall()

            if results:
                print("\nTop Borrowed Books:")
                print("=" * 60)
                print(f"{'Rank':<5}{'Book ID':<10}{'Title':<30}{'Borrow Count':<15}")
                print("-" * 60)
                for rank, row in enumerate(results[:limit], 1):
                    print(f"{rank:<5}{row[0]:<10}{row[1]:<30}{row[2]:<15}")
                print("=" * 60)
            else:
                print("No data available.")

@handle_database_errors
def most_active_members() -> None:
    """Display the members who borrow the most books."""
    with get_connection() as cnx:
        if cnx is None:
            return
        with cnx.cursor() as cursor:
            print("\n--- Most Active Members ---")
            limit = get_valid_number("Enter number of top members to display (default 10): ", int, True) or 10
            if limit <= 0:
                print("Limit must be positive!")
                return

            ref_cursor = cursor.var(cx_Oracle.CURSOR)
            cursor.callproc("MostActiveMembers", [ref_cursor])
            results = ref_cursor.getvalue().fetchall()

            if results:
                print("\nTop Borrowers:")
                print("=" * 70)
                print(f"{'Rank':<5}{'Member ID':<10}{'Name':<25}{'Borrow Count':<15}")
                print("-" * 70)
                for rank, row in enumerate(results[:limit], 1):
                    print(f"{rank:<5}{row[0]:<10}{row[1]:<25}{row[2]:<15}")
                print("=" * 70)
            else:
                print("No data available.")

@handle_database_errors
def books_issued_last_month() -> None:
    """Display books issued in the last month."""
    with get_connection() as cnx:
        if cnx is None:
            return
        with cnx.cursor() as cursor:
            print("\n--- Books Issued Last Month ---")
            ref_cursor = cursor.var(cx_Oracle.CURSOR)
            cursor.callproc("BooksIssuedLastMonth", [ref_cursor])
            results = ref_cursor.getvalue().fetchall()

            if results:
                print("\nRecently Issued Books:")
                print("=" * 60)
                print(f"{'Book ID':<10}{'Title':<30}")
                print("-" * 60)
                for row in results:
                    print(f"{row[0]:<10}{row[1]:<30}")
                print("=" * 60)
            else:
                print("No books were issued last month.")

# Book Cart and Issue Management
class BookCart:
    """Class to manage a user's book cart."""
    def __init__(self, mno: str):
        self.mno = mno
        self.items: List[Tuple[str, str]] = []

    def add_book(self, book_code: str, book_title: str) -> None:
        self.items.append((book_code, book_title))

    def remove_book(self, index: int) -> bool:
        if 0 <= index < len(self.items):
            self.items.pop(index)
            return True
        return False

    def clear(self) -> None:
        self.items.clear()

    def display(self) -> None:
        if not self.items:
            print("Your cart is empty")
            return
        print("\nBooks in your cart:")
        for idx, (code, title) in enumerate(self.items, 1):
            print(f"{idx}. {code} - {title}")

@handle_database_errors
def show_available_books() -> List[Tuple[str, str]]:
    """Display all available books."""
    with get_connection() as cnx:
        if cnx is None:
            return []
        with cnx.cursor() as cursor:
            cursor.execute("""
                SELECT BNO, BNAME FROM BookRecord
                WHERE BNO NOT IN (
                    SELECT BNO FROM Issue WHERE RETURN_DATE IS NULL
                )
                ORDER BY BNAME
            """)
            return cursor.fetchall()

@handle_database_errors
def issue_books(mno: str, book_cart: BookCart) -> None:
    """Process book issue for a member."""
    if not book_cart.items:
        print("No books in cart to issue")
        return

    with get_connection() as cnx:
        if cnx is None:
            return
        with cnx.cursor() as cursor:
            user_id = input("Enter User ID performing action: ").strip()
            cursor.execute("""
                SELECT MNAME, 
                       (SELECT COUNT(*) FROM Issue i 
                        WHERE i.MNO = u.MNO AND i.RETURN_DATE IS NULL) as ACTIVE_ISSUES
                FROM Users u
                WHERE u.MNO = :mno
            """, {'mno': mno})
            member = cursor.fetchone()

            if not member:
                print("Member not found!")
                return

            mname, active_issues = member
            max_books = 5
            if active_issues + len(book_cart.items) > max_books:
                print(f"Error: You can only borrow {max_books - active_issues} more books")
                return

            print(f"\nIssuing books for: {mname} (ID: {mno})")
            issue_date = datetime.now().date()
            due_date = issue_date + timedelta(days=14)

            for book_code, book_title in book_cart.items:
                cursor.execute("""
                    SELECT BNO FROM BookRecord WHERE BNO = :bno
                    AND BNO NOT IN (SELECT BNO FROM Issue WHERE RETURN_DATE IS NULL)
                """, {'bno': book_code})
                if not cursor.fetchone():
                    print(f"Book not available: {book_title}")
                    continue

                issue_id_var = cursor.var(cx_Oracle.NUMBER)
                cursor.execute("""
                    INSERT INTO Issue (MNO, BNO, ISSUE_DATE)
                    VALUES (:mno, :bno, :issue_date)
                    RETURNING ISSUE_ID INTO :issue_id
                """, {'mno': mno, 'bno': book_code, 'issue_date': issue_date, 'issue_id': issue_id_var})
                issue_id = issue_id_var.getvalue()[0]

                cursor.execute("""
                    INSERT INTO Return (ISSUE_ID, DUE_DATE)
                    VALUES (:issue_id, :due_date)
                """, {'issue_id': issue_id, 'due_date': due_date})

                print(f"Issued: {book_title} (Return by: {due_date})")
                log_action("ISSUE_BOOK", user_id, f"Issued book {book_code} - {book_title} to member {mno}")

            cnx.commit()
            book_cart.clear()
            print("\nAll books issued successfully!")
            print(f"Please return by: {due_date}")

# Menu Functions
def user_management_menu() -> None:
    """Display the user management menu."""
    options = {
        "1": insert_user,
        "2": update_user,
        "3": delete_user,
        "4": search_user,
        "5": view_audit_history
    }
    while True:
        clear_screen()
        print("\n--- User Management ---")
        print("1. Add New Member")
        print("2. Update Member")
        print("3. Delete Member")
        print("4. Search Member")
        print("5. View Audit History")
        print("6. Return to Main Menu")
        
        choice = input("Enter your choice (1-6): ").strip()
        if choice == "6":
            break
        elif choice in options:
            options[choice]()
        else:
            print("Invalid choice. Please try again.")
        input("\nPress Enter to continue...")

def catalog_management_menu() -> None:
    """Display the catalog management menu."""
    options = {
        "1": insert_book,
        "2": update_book,
        "3": delete_book,
        "4": search_book,
        "5": view_audit_history
    }
    while True:
        clear_screen()
        print("\n--- Catalog Management ---")
        print("1. Add New Book")
        print("2. Update Book")
        print("3. Delete Book")
        print("4. Search Book")
        print("5. View Audit History")
        print("6. Return to Main Menu")
        
        choice = input("Enter your choice (1-6): ").strip()
        if choice == "6":
            break
        elif choice in options:
            options[choice]()
        else:
            print("Invalid choice. Please try again.")
        input("\nPress Enter to continue...")

def fine_management_menu() -> None:
    """Display the fine management menu."""
    while True:
        clear_screen()
        print("\n--- Fine Management ---")
        print("1. Calculate Fines")
        print("2. Pay Fines")
        print("3. View Fine History")
        print("4. View Audit History")
        print("5. Return to Main Menu")
        
        choice = input("Enter your choice (1-5): ").strip()
        if choice == "5":
            break
        elif choice in ["1", "2", "3", "4"]:
            if choice in ["1", "2", "3"]:
                mno = input("Enter Member Code: ").strip()
                if not mno:
                    print("Member Code cannot be empty!")
                    continue
                if choice == "1":
                    calculate_fine_for_member(mno)
                elif choice == "2":
                    pay_fine(mno)
                else:
                    view_fine_history(mno)
            else:  # choice == "4"
                view_audit_history()
        else:
            print("Invalid choice. Please try again.")
        input("\nPress Enter to continue...")

def reporting_menu() -> None:
    """Display the reporting menu."""
    options = {
        "1": most_popular_books,
        "2": most_active_members,
        "3": books_issued_last_month,
        "4": view_audit_history
    }
    while True:
        clear_screen()
        print("\n--- Reporting ---")
        print("1. Most Popular Books")
        print("2. Most Active Members")
        print("3. Recently Issued Books")
        print("4. View Audit History")
        print("5. Return to Main Menu")
        
        choice = input("Enter your choice (1-5): ").strip()
        if choice == "5":
            break
        elif choice in options:
            options[choice]()
        else:
            print("Invalid choice. Please try again.")
        input("\nPress Enter to continue...")

def issue_management_menu(mno: str) -> None:
    """Menu for book issuing process."""
    cart = BookCart(mno)
    while True:
        clear_screen()
        print("\n=== Book Issue System ===")
        print("1. View Available Books")
        print("2. View Your Cart")
        print("3. Add Book to Cart")
        print("4. Remove Book from Cart")
        print("5. Checkout")
        print("6. View Audit History")
        print("7. Return to Main Menu")
        
        choice = input("Enter your choice (1-7): ").strip()
        if choice == "7":
            break
        elif choice == "6":
            view_audit_history()
        elif choice == "1":
            print("\nAvailable Books:")
            print("=" * 60)
            print(f"{'Code':<10}{'Title':<35}")
            print("-" * 60)
            for bno, bname in show_available_books():
                print(f"{bno:<10}{bname:<35}")
            print("=" * 60)
        elif choice == "2":
            cart.display()
        elif choice == "3":
            bno = input("Enter book code to add: ").strip()
            if not bno:
                print("Book code cannot be empty!")
                continue
            books = show_available_books()
            book_found = next((b for b in books if b[0] == bno), None)
            if book_found:
                cart.add_book(book_found[0], book_found[1])
                print(f"Added: {book_found[1]}")
            else:
                print("Invalid book code or book not available")
        elif choice == "4":
            cart.display()
            if cart.items:
                try:
                    idx = int(input("Enter item number to remove: ")) - 1
                    if cart.remove_book(idx):
                        print("Book removed from cart")
                    else:
                        print("Invalid item number")
                except ValueError:
                    print("Please enter a valid number")
        elif choice == "5":
            issue_books(mno, cart)
        else:
            print("Invalid choice")
        input("\nPress Enter to continue...")

# Main Menu
def main() -> None:
    """Main program loop with comprehensive error handling."""
    try:
        while True:
            clear_screen()
            print("\n=== Library Management System ===")
            print("1. User Management")
            print("2. Catalog Management")
            print("3. Issue Management")
            print("4. Fine Management")
            print("5. Reporting")
            print("6. View Audit History")
            print("9. Exit")
            
            choice = input("\nEnter your choice (1-6, 9): ").strip()
            if choice == "9":
                print("\nThank you for using the Library Management System. Goodbye!")
                break
            elif choice == "6":
                view_audit_history()
            elif choice in ["1", "2", "3", "4", "5"]:
                if choice == "1":
                    user_management_menu()
                elif choice == "2":
                    catalog_management_menu()
                elif choice == "3":
                    mno = input("Enter your member ID: ").strip()
                    if not mno:
                        print("Member ID cannot be empty!")
                    else:
                        issue_management_menu(mno)
                elif choice == "4":
                    fine_management_menu()
                elif choice == "5":
                    reporting_menu()
            else:
                print("Invalid choice. Please try again.")
            input("\nPress Enter to continue...")
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nCritical system failure: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
