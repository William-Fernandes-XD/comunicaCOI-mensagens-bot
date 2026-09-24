const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const readline = require('readline');
const fs = require('fs');

// Evitar erros de no such file or directory, criando a pasta se não existir
fs.mkdirSync('./contatos', { recursive: true });

// Aqui salvamos um LocalAuth para podermos manter a sessão do whatsapp
const client = new Client({
    authStrategy: new LocalAuth({
        clientId: "cache_usuario_whatsapp"
    })
});

// leitura de entrada do usuário
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

client.on('qr', (qr) => {
    qrcode.generate(qr, { small: true });
});

// será usado no arquivo de server.js para bloquear posts enquanto o cliente não estiver pronto
let isReady = false;

client.on('ready', () => {

    console.log('Whatsapp iniciado com sucesso!');
    isReady = true;
   
    client.getContacts().then((contacts) => {
        contacts.forEach((contact) => {
            // salvando os grupos no arquivo de grupos
            if(contact.isGroup) {
                fs.appendFileSync('./contatos/grupos.txt', `${contact.name} - ${contact.id.user} - ${contact.id._serialized}\n`);
            }else{
                // salvando os contatos no arquivo de contatos
                fs.appendFileSync('./contatos/contatos.txt',
                    `Nome: ${contact.name || contact.pushname || contact.number}
                    Número: ${contact.number}
                    ID: ${contact.id._serialized}
                    ------------------------------
                    `
                );

            }

        });
        console.log('Contatos e grupos salvos nos arquivos contatos.txt e grupos.txt');
    });
});

client.initialize();

// exportando o client para ser usado em server.js
module.exports = { client, isReady: () => isReady };