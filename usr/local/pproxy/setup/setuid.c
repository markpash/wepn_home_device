#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>

#define SRV_CNT 5
#define CMD_CNT 6
#define SPECIAL_CMD_CNT 14

int sanitize(char* input) {
	static char ok_chars[] = "abcdefghijklmnopqrstuvwxyz"
		"ABCDEFGHIJKLMNOPQRSTUVWXYZ"
		"1234567890_-.@+=/";
	char user_data[] = "Bad char 1:} Bad char 2:{ bad char3: /  char4:\\";
	char *cp = user_data; /* Cursor into string */
	const char *end = user_data + strlen( user_data);
	int i = 0;
	while (input[i] != '\0') {
		if (strchr(ok_chars, input[i]) == NULL) {
			//illegal character, remove
			input[i] = '_';
		}
		i++;
	}
	puts(input);
	return i;
}



int main(int argc, char * argv[])
{
	FILE *p;
	int ch;
	int i = 0;
	const char* services[SRV_CNT];
	services[0]="openvpn";
	services[1]="shadowsocks-libev";
	services[2]="wg-quick@wg0";
	services[3]="tor";
	services[4]="sshd";


	const char* commands[CMD_CNT];
	commands[0]="stop";
	commands[1]="start";
	commands[2]="restart";
	commands[3]="reload";
	commands[4]="enable";
	commands[5]="disable";


	const char* scommands[SPECIAL_CMD_CNT];
	scommands[0]="/sbin/poweroff";
	scommands[1]="/bin/sh /usr/local/sbin/restart-pproxy.sh";
	scommands[2]="/sbin/reboot";
	scommands[3]="/bin/sh /usr/local/sbin/update-pproxy.sh";
	scommands[4]="/bin/sh /usr/local/sbin/update-system.sh";
	scommands[5]= "/usr/local/sbin/wepn_git.sh";
	scommands[6]= "wg set wg0 peer %s allowed-ips 0.0.0.0/0";
	scommands[7]= "wg-quick save wg0";
	scommands[8]= "/bin/sh /usr/local/sbin/iptables-flush.sh";
	scommands[9]= "/bin/bash /usr/local/sbin/prevent_location_issue.sh";
	scommands[10]= "/bin/bash /usr/local/sbin/ip-shadow.sh";
	// hard coding sda1 since this command is primarily used in factory for provisioning configs
	scommands[11]= "mount -o umask=0022,gid=1001,uid=1001 /dev/sda1 /mnt/";
	scommands[12]= "umount /mnt/";
	scommands[13]= "ssh-keygen -A";

	int c,s,t;

	char cmd[255];

	if (argc != 4 && argc != 3 && argc != 5) {
		printf(" usage: ./run type service_identifier command_identifier");
		printf("\n* type: \n 0: services 1: special commands");

		printf("\n* services:\n");
		for (i=0; i < 3; i++){
			printf("%d: %s \t\t\n", i, services[i]);
		}
		printf("\n* commands:\n");
		for (i=0; i < CMD_CNT; i++){
			printf("%d: %s\t\t\n", i, commands[i]);
		}
		printf("\n* special commands: \n");
		for (i=0; i < SPECIAL_CMD_CNT; i++){
			printf("%d: ", i);
			printf(": ");
			puts(scommands[i]);
			printf("\t\t\n");
		}
		printf("\n");
		return(0);
	}
	char* ptr;
	t = strtol(argv[1], &ptr, 10);
	s = strtol(argv[2], &ptr, 10);




	if (s > SPECIAL_CMD_CNT || t > 3) {
		printf("S=%d T=%d\n", s, t);
		printf("# commands = %d\n", SPECIAL_CMD_CNT);
		printf("Out of range index\n");
		return(-1);
	}

	if (t == 0) {
		c = strtol(argv[3], &ptr, 10);
		if (c > CMD_CNT) {
			printf("Out of range commands index\n");
			return(-1);
		}
		sprintf(cmd, "systemctl %s %s", commands[c], services[s]); 
	}
	if (t == 1) {
		if (argc == 4 && s == 6) {
			printf("\noriginal: %s\nduring: \n", argv[3]);
			sanitize(argv[3]);
			printf("\nafter: %s\n", argv[3]);
			sprintf(cmd, scommands[6], argv[3]);
		 } else {
			sprintf(cmd, "%s", scommands[s]);
		 }
	}
	printf("\ncmd= %s\n", cmd);
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
