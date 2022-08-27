/*
 * Data:                2009-02-10
 * Autor:               Jakub Gasior <quebes@mars.iti.pk.edu.pl>
 * Kompilacja:          $ gcc server2.c -o server2
 * Uruchamianie:        $ ./server2 <numer portu>
 */

#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h> /* socket() */
#include <netinet/in.h> /* struct sockaddr_in */
#include <arpa/inet.h>  /* inet_ntop() */
#include <unistd.h>     /* close() */
#include <string.h>
#include <errno.h>

int main(int argc, char** argv) {

    int             sockfd; /* Deskryptor gniazda. */
    int             retval; /* Wartosc zwracana przez funkcje. */

    /* Gniazdowe struktury adresowe (dla klienta i serwera): */
    struct          sockaddr_in client_addr, server_addr;

    /* Rozmiar struktur w bajtach: */
    socklen_t       client_addr_len, server_addr_len;

    /* Bufor wykorzystywany przez recvfrom() i sendto(): */
    char            buff[256];

    /* Bufor dla adresu IP klienta w postaci kropkowo-dziesietnej: */
    char            addr_buff[256];


    if (argc != 2) {
        fprintf(stderr, "Invocation: %s <PORT>\n", argv[0]);
        exit(EXIT_FAILURE);
    }

    /* Utworzenie gniazda dla protokolu UDP: */
    sockfd = socket(PF_INET, SOCK_DGRAM, 0);
    if (sockfd == -1) {
        perror("socket()");
        exit(EXIT_FAILURE);
    }

    /* Wyzerowanie struktury adresowej serwera: */
    memset(&server_addr, 0, sizeof(server_addr));
    /* Domena komunikacyjna (rodzina protokolow): */
    server_addr.sin_family          =       AF_INET;
    /* Adres nieokreslony (ang. wildcard address): */
    server_addr.sin_addr.s_addr     =       htonl(INADDR_ANY);
    /* Numer portu: */
    server_addr.sin_port            =       htons(atoi(argv[1]));
    /* Rozmiar struktury adresowej serwera w bajtach: */
    server_addr_len                 =       sizeof(server_addr);

    /* Powiazanie "nazwy" (adresu IP i numeru portu) z gniazdem: */
    if (bind(sockfd, (struct sockaddr*) &server_addr, server_addr_len) == -1) {
        perror("bind()");
        exit(EXIT_FAILURE);
    }
    
    
      client_addr_len = sizeof(client_addr);


while(1){
    fprintf(stdout, "Server is listening for incoming connection...\n");

  

    /* Oczekiwanie na dane od klienta: */
    retval = recvfrom(
                 sockfd,
                 buff, sizeof(buff),
                 0,
                 (struct sockaddr*)&client_addr, &client_addr_len
             );
    if (retval == -1) {
        perror("recvfrom()");
        exit(EXIT_FAILURE);
    }

    fprintf(stdout, "UDP datagram received from %s:%d. Echoing message...\n",
            inet_ntop(AF_INET, &client_addr.sin_addr, addr_buff, sizeof(addr_buff)),
            ntohs(client_addr.sin_port)
           );

    sleep(5);
    
    if(retval==0){
    fprintf(stdout, "Wyslano pusta wiadomosc!!!!!!\n");
    break;
    }
    else{
    fprintf(stdout, "Otrzymano wiadomosc: %s", buff);
    fprintf(stdout, "Rozmiar w bajtach:%d\n", retval);
    fflush(stdout);
    }
    
    sleep(2);
    fprintf(stdout, "Sprawdzanie czy wiadomosc jest palindromem....\n");
    sleep(2);
    
    
    retval= is_palindrome(buff, retval);
    memset(buff, 0, 256);
    
    if(retval==-1) {fprintf(stdout, " -Wprowadzone dane sa bledne!!!\n"); 
    sprintf(buff, "Wprowadzone dane sa bledne!!!\n");}
    
       else if(retval==1) {fprintf(stdout, " -To jest palindrom!!!\n"); 
    sprintf(buff, "To jest palindrom!!!\n");}
    
        else {fprintf(stdout, " -To nie jest palindrom!!!\n"); 
    sprintf(buff, "To nie jest palindrom!!!\n");}
    
    
    fflush(stdout);

    /* Wyslanie odpowiedzi (echo): */
    retval = sendto(
                 sockfd,
                 buff, strlen(buff),
                 0,
                 (struct sockaddr*)&client_addr, client_addr_len
             );
    if (retval == -1) {
        perror("sendto()");
        exit(EXIT_FAILURE);
    }

}
    close(sockfd);

    exit(EXIT_SUCCESS);
}
