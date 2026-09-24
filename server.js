const express = require('express');
const {client, isReady} = require('./iniciar_whatsapp');

const app = express();

app.use(express.json());

app.post('/enviar', async(req, res) => {

    const { chatId, message, mentions, regional } = req.body;
    
    if(!isReady()) {
        return res.status(500).json({ error: 'O cliente do WhatsApp não está pronto. Por favor, aguarde a inicialização.' });
    }

    try{

        const safeMentions = (mentions || []).map(n => {
            if(!n) return null;
            let id = n.includes('@c.us') ? n : `${n}@c.us`;
            return id;
        }).filter(Boolean);

        const mentionText = safeMentions.map(id => `@${id.split('@')[0]}`).join(' ');

        const finalMessage = `${message}\n\n${mentionText}`;

        await client.sendMessage(chatId, finalMessage, {
            mentions: safeMentions
        });

        console.log(`Mensagem enviada para: ${regional} || data: ${new Date().toISOString()}`);
        res.json({ ok: true });
    }catch(error){
        console.error('Erro ao enviar mensagem:', error);
        res.status(500).json({ error: 'Ocorreu um erro ao enviar a mensagem.' });
    }
});

app.listen(3020, () => {
    console.log('Servidor de mensagens rodando na porta 3020');
});