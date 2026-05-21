int main() {
    int arr[5];
    int i;

    /* fill and print */
    for (i = 0; i < 5; i++) {
        arr[i] = (i + 1) * 3;
    }
    for (i = 0; i < 5; i++) {
        printf("%d\n", arr[i]);
    }

    /* sum */
    int sum;
    sum = 0;
    for (i = 0; i < 5; i++) {
        sum += arr[i];
    }
    printf("%d\n", sum);

    /* string operations */
    char s[20];
    strcpy(s, "Hello");
    printf("%s\n", s);
    printf("%d\n", strlen(s));

    char t[20];
    strcpy(t, " World");
    strcat(s, t);
    printf("%s\n", s);

    return 0;
}
