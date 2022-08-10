#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>

int main(int argc, char * argv[])
{
	FILE *p;
	int ch;
	int i = 0;
	const char* services[3];
	services[0]="openvpn";
	services[1]="shadowsocks-libev";
	services[2]="wg-quick@wg0";


	const char* commands[4];
	commands[0]="stop";
	commands[1]="start";
	commands[2]="restart";
	commands[3]="reload";


	const char* scommands[6];
	scommands[0]="/sbin/poweroff";
	scommands[1]="/usr/local/sbin/restart-pproxy.sh";
	scommands[2]="/sbin/reboot";
	scommands[3]="/bin/sh /usr/local/sbin/update-pproxy.sh";
	scommands[4]="/bin/sh /usr/local/sbin/update-system.sh";
	scommands[5]= "/usr/local/sbin/wepn_git.sh";

	int c,s,t;

	char cmd[100];    

	if (argc != 4 && argc != 3) {
		printf(" usage: ./run type service_identifier command_identifier");
		printf("\n* type: \n 0: services 1: special commands");

		printf("\n* services:\n");
		for (i=0; i < 3; i++){
			printf("%d: ", i);
			printf(services[i]);
			printf("\t ");
		}
		printf("\n* commands:\n");
		for (i=0; i < 3; i++){
			printf("%d: ", i);
			printf(": ");
			printf(commands[i]);
			printf("\t ");
		}
		printf("\n* special commands: \n");
		for (i=0; i < 3; i++){
			printf("%d: ", i);
			printf(": ");
			printf(scommands[i]);
			printf("\t ");
		}
		printf("\n");
		return(0);
	}
	char* ptr;
	t = strtol(argv[1], &ptr, 10);
	s = strtol(argv[2], & ptr, 10);
	c = strtol(argv[3], &ptr, 10);



	if (c > 3 || s > 2 || t > 6) {
		return(-1);
	}

	if (t == 0) {
		sprintf(cmd, "systemctl %s %s", commands[c], services[s]); 
	}
	if (t == 1) {
		sprintf(cmd, "%s", scommands[s]); 
	}
	//printf(cmd);
	printf("\n");
	setuid(0);
	p = popen(cmd,"r");
	if ( p == NULL )
	{
		puts("Unable to open process");
		return(1);
	}
	while( (ch=fgetc(p)) != EOF)
		putchar(ch);
	pclose(p);

	return(0);
}
