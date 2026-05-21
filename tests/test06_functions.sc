int factorial(int n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
}

int gcd(int a, int b) {
    while (b != 0) {
        int t;
        t = b;
        b = a % b;
        a = t;
    }
    return a;
}

int is_even(int n) {
    if (n % 2 == 0) return 1;
    return 0;
}

int main() {
    printf("%d\n", factorial(1));
    printf("%d\n", factorial(5));
    printf("%d\n", factorial(10));

    printf("%d\n", gcd(12, 8));
    printf("%d\n", gcd(100, 75));
    printf("%d\n", gcd(17, 5));

    printf("%d\n", is_even(4));
    printf("%d\n", is_even(7));

    return 0;
}
