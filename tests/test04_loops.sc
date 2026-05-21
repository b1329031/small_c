int main() {
    int i;
    int sum;

    /* while loop */
    sum = 0;
    i = 1;
    while (i <= 5) {
        sum += i;
        i++;
    }
    printf("%d\n", sum);

    /* for loop */
    sum = 0;
    for (i = 1; i <= 10; i++) {
        sum += i;
    }
    printf("%d\n", sum);

    /* do-while */
    sum = 0;
    i = 0;
    do {
        i++;
        sum += i;
    } while (i < 4);
    printf("%d\n", sum);

    /* break */
    sum = 0;
    for (i = 1; i <= 10; i++) {
        if (i == 6) break;
        sum += i;
    }
    printf("%d\n", sum);

    /* continue */
    sum = 0;
    for (i = 1; i <= 10; i++) {
        if (i % 2 == 0) continue;
        sum += i;
    }
    printf("%d\n", sum);

    return 0;
}
