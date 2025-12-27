from database.database import init_db, get_db
from database.models import User, CommunicationChannel

def main():
    # Initialize the database (creates tables if they don't exist)
    init_db()

    # Get a new database session
    db = next(get_db())

    # Check if user already exists
    existing_user = db.query(User).filter(User.gmail == "example@gmail.com").first()

    if not existing_user:
        # Create a new user
        new_user = User(
            gmail="example@gmail.com",
            phone_number="1234567890",
            slack_id="U123ABC456"
        )

        # Add user to the session
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        print(f"Created user: {new_user}")

        # Add an additional communication channel
        new_channel = CommunicationChannel(
            user_id=new_user.id,
            channel_type="telegram",
            channel_identifier="@example_user"
        )
        db.add(new_channel)
        db.commit()
        db.refresh(new_channel)
        print(f"Added communication channel: {new_channel} for user {new_user.gmail}")

    else:
        print(f"User {existing_user.gmail} already exists.")

    # Query and print all users and their channels
    print("\n--- All Users and Channels in DB ---")
    all_users = db.query(User).all()
    for user in all_users:
        print(f"User: {user.gmail}, Phone: {user.phone_number}, Slack ID: {user.slack_id}")
        for channel in user.communication_channels:
            print(f"  - Channel: {channel.channel_type}, Identifier: {channel.channel_identifier}")
    print("------------------------------------\n")

    # Close the session
    db.close()

if __name__ == "__main__":
    main()
