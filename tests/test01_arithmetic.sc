#define MAX 100
#define BASE 0x10

int main() {
    int a;
    int b;
    int c;
    a = 42;
    b = 13;
    c = a + b;
    printf("%d\n", c);
    c = a - b;
    printf("%d\n", c);
    c = a * b;
    printf("%d\n", c);
    c = a / b;
    printf("%d\n", c);
    c = a % b;
    printf("%d\n", c);

    /* compound assignment */
    c = 10;
    c += 5;
    printf("%d\n", c);
    c -= 3;
    printf("%d\n", c);
    c *= 2;
    printf("%d\n", c);
    c /= 4;
    printf("%d\n", c);
    c %= 3;
    printf("%d\n", c);

    /* hex constant via #define */
    printf("%d\n", BASE);
    printf("%d\n", MAX);

    return 0;
}
