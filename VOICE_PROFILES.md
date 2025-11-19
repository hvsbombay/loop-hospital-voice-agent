# 🎭 Voice Assistant Profiles

Loop AI now includes **3 distinct voice assistant profiles** to personalize your experience!

## Available Profiles

### 👩‍⚕️ **Sarah** - Friendly Female (Default)
- **Voice Type**: Female
- **Characteristics**: 
  - Speaking Rate: Normal (1.0x)
  - Pitch: Slightly Higher (1.1x)
  - Style: Warm, friendly, and approachable
- **Best For**: General queries, comfortable conversation
- **Personality**: Friendly healthcare assistant with a warm tone

### 👨‍⚕️ **Dr. James** - Professional Male
- **Voice Type**: Male
- **Characteristics**:
  - Speaking Rate: Slightly Slower (0.95x)
  - Pitch: Lower (0.9x)
  - Style: Professional, authoritative, and clear
- **Best For**: Detailed medical information, professional context
- **Personality**: Experienced doctor with a calm, professional demeanor

### 👩‍💼 **Emma** - Energetic Female
- **Voice Type**: Female
- **Characteristics**:
  - Speaking Rate: Faster (1.1x)
  - Pitch: Higher (1.2x)
  - Style: Energetic, enthusiastic, and dynamic
- **Best For**: Quick queries, upbeat interactions
- **Personality**: Energetic assistant with a cheerful, lively tone

## How to Use

1. **Open the Voice Assistant**: Navigate to http://localhost:8080
2. **Select Your Preferred Voice**: Click on any of the three voice profiles at the top
3. **Test the Voice**: Each profile will introduce themselves when selected
4. **Start Conversing**: Use the microphone or text input to ask questions

## Technical Details

The voice profiles use the Web Speech API with customized parameters:

```javascript
{
  rate: 0.95-1.1,  // Speech speed
  pitch: 0.9-1.2,  // Voice pitch
  voice: Auto-selected based on browser's available voices
}
```

The system intelligently selects the best matching voice from your browser's available voices based on the profile type (male/female) and language (English).

## Browser Compatibility

Voice profiles work with all modern browsers that support the Web Speech API:
- ✅ Chrome/Edge (Best support)
- ✅ Safari
- ✅ Firefox (Limited voice options)
- ⚠️ HTTPS required for microphone access (or localhost)

## Features

- **Instant Profile Switching**: Change voices mid-conversation
- **Audio Feedback**: Each profile introduces itself when selected
- **Persistent Selection**: Your chosen profile remains active throughout the session
- **Adaptive Voice Selection**: Automatically picks the best available voice for each profile

## Example Queries

Try these with different voice profiles to hear the difference:

```
"Tell me hospitals in Mumbai"
"Is there any Kapoor Medical Centre in database?"
"Show me hospitals around Bangalore"
"Tell me more about Manipal"
```

---

**Note**: Voice quality and availability depend on your operating system and browser. Some browsers may have limited voice options, but the system will always provide the best available match.
