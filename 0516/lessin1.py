import random

def guess_number_game():
    secret = random.randint(1, 100)
    attempts = 0
    max_attempts = 10

    print("=== 猜數字遊戲 ===")
    print(f"我已經想好一個 1 到 100 之間的數字，你有 {max_attempts} 次機會猜中它！")

    while attempts < max_attempts:
        remaining = max_attempts - attempts
        try:
            guess = int(input(f"\n剩餘 {remaining} 次機會，請輸入你的猜測："))
        except ValueError:
            print("請輸入有效的數字！")
            continue

        attempts += 1

        if guess < secret:
            print("太小了！再大一點。")
        elif guess > secret:
            print("太大了！再小一點。")
        else:
            print(f"\n恭喜你！答對了！答案就是 {secret}，你用了 {attempts} 次猜中！")
            return

    print(f"\n很遺憾，你用完了所有機會。正確答案是 {secret}。")

if __name__ == "__main__":
    while True:
        guess_number_game()
        again = input("\n要再玩一次嗎？(y/n)：").strip().lower()
        if again != "y":
            print("感謝遊玩，掰掰！")
            break
