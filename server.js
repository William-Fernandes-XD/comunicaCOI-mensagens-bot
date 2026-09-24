const express = require('express');
const client = require('./iniciar_whatsapp');

const app = express();

app.use(express.json());

app.post('/enviar', async(req, res) => {
    
    if(!client.isReady) {
        return res.status(500).json({ error: 'O cliente do WhatsApp não está pronto. Por favor, aguarde a inicialização.' });
    }

    try{

        

    }catch(error){
        console.error('Erro ao enviar mensagem:', error);
        res.status(500).json({ error: 'Ocorreu um erro ao enviar a mensagem.' });
    }
});

app.listen(3020, () => {
    console.log('Servidor de mensagens rodando na porta 3020');
});