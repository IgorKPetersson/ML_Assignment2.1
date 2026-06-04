import random

# A small list of words for Hangman
WORD_LIST = [
    'python', 'hangman', 'challenge', 'programming', 'agent', 'computer', 'game', 'keyboard'
]


def get_random_word():
    """Select a random word from the list."""
    return random.choice(WORD_LIST)


def display_current_state(word, guessed_letters):
    """Return a string showing the word with guessed letters and underscores."""
    return ' '.join(c if c in guessed_letters else '_' for c in word)


def hangman():
    print("Welcome to Hangman!")
    word = get_random_word()
    guessed_letters = set()
    wrong_guesses = 0
    max_wrong_guesses = 6

    while wrong_guesses < max_wrong_guesses:
        print("\nWord:", display_current_state(word, guessed_letters))
        print(f"Wrong guesses left: {max_wrong_guesses - wrong_guesses}")
        guess = input("Guess a letter: ").lower()

        if len(guess) != 1 or not guess.isalpha():
            print("Please enter a single alphabetic letter.")
            continue

        if guess in guessed_letters:
            print("You already guessed that letter. Try again.")
            continue

        if guess in word:
            guessed_letters.add(guess)
            print("Good guess!")
        else:
            wrong_guesses += 1
            print(f"Wrong guess! {guess} is not in the word.")
            guessed_letters.add(guess)

        if all(c in guessed_letters for c in word):
            print(f"\nCongratulations! You guessed the word '{word}' correctly!")
            break

    else:
        print(f"\nGame over! The word was '{word}'. Better luck next time.")


if __name__ == '__main__':
    hangman()
