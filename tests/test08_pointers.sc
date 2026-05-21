void swap(int *a, int *b) {
    int tmp;
    tmp = *a;
    *a = *b;
    *b = tmp;
}

void fill(int *arr, int n, int val) {
    int i;
    for (i = 0; i < n; i++) {
        arr[i] = val;
    }
}

int main() {
    int x;
    int y;
    x = 3;
    y = 7;
    printf("%d %d\n", x, y);
    swap(&x, &y);
    printf("%d %d\n", x, y);

    int buf[4];
    fill(buf, 4, 99);
    int i;
    for (i = 0; i < 4; i++) {
        printf("%d\n", buf[i]);
    }

    /* pointer arithmetic / address-of */
    int *p;
    p = &x;
    printf("%d\n", *p);
    *p = 42;
    printf("%d\n", x);

    return 0;
}
