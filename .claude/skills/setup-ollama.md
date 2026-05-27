---
name: Setup Ollama
description: Install and configure Ollama for local LLM inference
type: skill
---

# Setup Ollama Skill

Guides installing and configuring Ollama to power the Course Materials RAG system.

## What is Ollama?

Ollama runs large language models locally on your machine:
- **No API costs** - Models run on your hardware
- **Private** - Data stays on your computer
- **Offline capable** - No internet required after setup
- **Flexible** - Easy model switching

## Installation

### Windows
1. Download from [ollama.ai/download](https://ollama.ai/download)
2. Run installer and follow prompts
3. Restart terminal/IDE after installation

### macOS
```bash
# Using Homebrew
brew install ollama

# Or download from ollama.ai/download
```

### Linux
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

## Starting Ollama

In a terminal, start the Ollama server:
```bash
ollama serve
```

Expected output:
```
2024/01/15 10:30:45 loaded the model
2024/01/15 10:30:46 listening on 127.0.0.1:11434
```

**Keep this terminal running** while using the RAG application.

## Installing Models

In a **separate terminal**, pull a model:

### Option 1: llama2 (Recommended for this project)
```bash
ollama pull llama2
```
- **Size**: ~4GB
- **Speed**: Moderate (~5-10s per response)
- **Quality**: Good for course Q&A
- **RAM required**: 8GB+

### Option 2: mistral (Faster alternative)
```bash
ollama pull mistral
```
- **Size**: ~5GB
- **Speed**: Fast (~2-5s per response)
- **Quality**: Very good
- **RAM required**: 8GB+

### Option 3: neural-chat (Conversation optimized)
```bash
ollama pull neural-chat
```
- **Size**: ~4GB
- **Speed**: Moderate
- **Quality**: Optimized for dialogue
- **RAM required**: 6GB+

### Checking Downloaded Models
```bash
ollama list
```

## Configuration

### Update .env File

Create `.env` in project root:
```bash
# Use default Ollama location
OLLAMA_API_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# Or use a different model
OLLAMA_MODEL=mistral
OLLAMA_MODEL=neural-chat
```

### Change Models at Runtime
1. Update `.env` with different `OLLAMA_MODEL`
2. Restart the RAG server
3. Model automatically switches on next request

## Troubleshooting

### "Cannot connect to Ollama"
**Issue**: Server shows error about Ollama API

**Solution**:
1. Verify `ollama serve` is running in another terminal
2. Check API is accessible: 
   ```bash
   curl http://localhost:11434/api/tags
   ```
3. If using custom port, update `OLLAMA_API_URL` in `.env`

### "Model not found"
**Issue**: Error says `llama2` not found

**Solution**:
```bash
ollama pull llama2
# Wait for download to complete (several minutes)
```

### Slow Responses (10+ seconds)
**Possible causes**:
- First response is always slower (model loading)
- Insufficient RAM (recommendation: 8GB+)
- CPU bottleneck on older machines
- Model still downloading in background

**Solutions**:
1. Try smaller model (mistral is faster)
2. Check system resources
3. Increase available RAM
4. Wait for model to fully load

### High Memory Usage
**Issue**: System memory maxed out

**Solution**:
- llama2 needs ~8GB
- Stop other applications
- Use smaller model (Neural-chat: ~6GB)
- Check `ollama serve` logs for memory info

## Hardware Requirements

| Model | Recommended RAM | Disk Space | Speed |
|-------|-----------------|-----------|-------|
| llama2 | 8GB+ | 4GB | Moderate |
| mistral | 8GB+ | 5GB | Fast |
| neural-chat | 6GB+ | 4GB | Moderate |

**Note**: Actual requirements vary by system. SSD recommended for faster loading.

## Performance Tuning

### Reduce Response Time
In `.env`:
```bash
# Use faster model
OLLAMA_MODEL=mistral
```

### Improve Response Quality
```bash
# Use larger context model (if 16GB+ RAM)
OLLAMA_MODEL=llama2
# or
OLLAMA_MODEL=mistral
```

## Verification

Once Ollama is running and model is installed:

1. **Verify API**:
   ```bash
   curl -X POST http://localhost:11434/api/chat \
     -H "Content-Type: application/json" \
     -d '{"model": "llama2", "messages": [{"role": "user", "content": "hello"}], "stream": false}'
   ```

2. **Start RAG server**:
   ```bash
   ./run.sh
   ```

3. **Test in browser**:
   - Open `http://localhost:8000`
   - Type a question
   - Should get response from Ollama (slower than Claude, but working!)

## Switching Between Models

1. Stop RAG server (`Ctrl+C`)
2. Pull new model (if needed): `ollama pull mistral`
3. Update `.env`: `OLLAMA_MODEL=mistral`
4. Restart server: `./run.sh`

## Model Selection Guide

**Choose llama2 if**:
- You want balanced speed/quality
- You have 8GB+ RAM
- First time user (default choice)

**Choose mistral if**:
- You want faster responses
- You have limited patience :)
- You have 8GB+ RAM

**Choose neural-chat if**:
- You want conversation-optimized responses
- You have 6GB+ RAM
- You prefer dialogue over Q&A

## Resources

- Ollama documentation: [ollama.ai/docs](https://ollama.ai/docs)
- Model library: [ollama.ai/library](https://ollama.ai/library)
- GitHub: [github.com/ollama/ollama](https://github.com/ollama/ollama)
