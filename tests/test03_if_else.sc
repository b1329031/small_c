int main() {
    int x;
    x = 10;

    if (x > 5) {
        printf("big\n");
    } else {
        printf("small\n");
    }

    if (x == 10) {
        printf("ten\n");
    } else if (x == 5) {
        printf("five\n");
    } else {
        printf("other\n");
    }

    /* switch / case with fall-through and break */
    int d;
    d = 2;
    switch (d) {
        case 1:
            printf("one\n");
            break;
        case 2:
            printf("two\n");
            break;
        case 3:
            printf("three\n");
            break;
        default:
            printf("other\n");
            break;
    }

    /* switch default */
    d = 9;
    switch (d) {
        case 1:
            printf("one\n");
            break;
        default:
            printf("default\n");
            break;
    }

    return 0;
}
