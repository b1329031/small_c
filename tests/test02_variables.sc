int main() {
    char c;
    int x;
    int y;

    c = 'A';
    printf("%c\n", c);
    c = c + 1;
    printf("%c\n", c);

    x = -7;
    y = abs(x);
    printf("%d\n", y);

    x = 9;
    y = sqrt(x);
    printf("%d\n", y);

    x = 2;
    y = pow(x, 8);
    printf("%d\n", y);

    /* bitwise */
    x = 0xF0;
    y = x & 0x0F;
    printf("%d\n", y);
    y = x | 0x0F;
    printf("%d\n", y);
    y = x ^ 0xFF;
    printf("%d\n", y);
    y = ~x;
    printf("%d\n", y);

    return 0;
}
