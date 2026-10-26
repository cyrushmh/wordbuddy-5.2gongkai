#include <stdio.h>
#include <string.h>
#include <pthread.h>

static int fact(int k){ return k<=1?1:k*fact(k-1); }
static int sq[4];
static void* work(void* a){ int i=*(int*)a; sq[i]=i*i; return NULL; }

int main(void){
    printf("LANG=C\n");
    int x=42; const char* s="hi"; int b=1; void* n=NULL;
    printf("LITERALS=%d,%s,%d,%p\n", x, s, b, (void*)n);
    printf("OPS=%d\n", 7*6+(int)strlen("abc"));
    int acc=0; for(int i=1;i<6;i++) acc+=i;
    printf("CONTROL=%d\n", acc);
    printf("FUNC=%d\n", fact(5));
    int arr[3]={1,2,3};
    printf("DATA=%zu,%d\n", sizeof(arr)/sizeof(arr[0]), arr[0]);
    FILE* f=fopen("/tmp/plang_c.txt","w"); fprintf(f,"io"); fclose(f);
    f=fopen("/tmp/plang_c.txt","r"); fclose(f); remove("/tmp/plang_c.txt");
    printf("IO=ok\n");
    FILE* bad=fopen("/nonexistent/plang","r");
    if(!bad) printf("ERROR=fopen-EACCES\n"); else fclose(bad);
    pthread_t t[4]; int idx[4];
    for(int i=0;i<4;i++){ idx[i]=i; pthread_create(&t[i],NULL,work,&idx[i]); }
    for(int i=0;i<4;i++) pthread_join(t[i],NULL);
    printf("CONCURRENCY=%d,%d,%d,%d\n", sq[0],sq[1],sq[2],sq[3]);
    return 0;
}
