import sys

from client import EchoSession


def main():
    if len(sys.argv) != 2:
        print("usage: python3 main.py <username>")
        sys.exit(1)

    username = sys.argv[1]
    session = EchoSession(username)
    print(f"Echo ready, acting as '{username}'. Ctrl+C or 'exit' to quit.\n")

    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            break

        reply = session.ask(user_input)
        print(f"echo> {reply}\n")


if __name__ == "__main__":
    main()