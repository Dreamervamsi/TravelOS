import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Animated,
  Easing,
  Pressable,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import {
  RecordingPresets,
  requestRecordingPermissionsAsync,
  setAudioModeAsync,
  useAudioRecorder,
  useAudioRecorderState,
} from 'expo-audio';
import type { AudioRecorder } from 'expo-audio';
import { File } from 'expo-file-system';
import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';

const API_BASE_URL = 'https://zany-space-xylophone-9pr7j679vr5f7jp9-8000.app.github.dev';
type Screen = 'home' | 'voice';
type VoiceStatus = 'starting' | 'listening' | 'sending' | 'stopped';

const trips = [
  { title: 'Kyoto Temple Walks', subtitle: 'Fushimi Inari, Gion alleys & tea ceremony moments.', place: 'JAPAN', colors: ['#EAA479', '#54433D', '#142F3A'] },
  { title: 'Amalfi Coast', subtitle: 'Sunlit villages, quiet coves & winding coastal roads.', place: 'ITALY', colors: ['#59B9C8', '#277E91', '#F2B37A'] },
  { title: 'Alpine Escape', subtitle: 'Mountain air, lake walks & postcard views.', place: 'SWITZERLAND', colors: ['#A6D3DC', '#427C8A', '#E5BD8C'] },
];

export default function App() {
  const [screen, setScreen] = useState<Screen>('home');
  const [status, setStatus] = useState<VoiceStatus>('starting');
  const [recording, setRecording] = useState<AudioRecorder | null>(null);
  const [error, setError] = useState('');
  const pulse = useRef(new Animated.Value(1)).current;
  const level = useRef(new Animated.Value(1)).current;
  const quietSince = useRef<number | null>(null);
  const heardSpeech = useRef(false);
  const closing = useRef(false);
  const recorder = useAudioRecorder({ ...RecordingPresets.HIGH_QUALITY, isMeteringEnabled: true });
  const recorderState = useAudioRecorderState(recorder, 250);

  useEffect(() => {
    if (screen !== 'voice' || status === 'stopped' || status === 'sending') return;
    const animation = Animated.loop(Animated.sequence([
      Animated.timing(pulse, { toValue: status === 'listening' ? 1.055 : 1.025, duration: 1100, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
      Animated.timing(pulse, { toValue: 1, duration: 1100, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
    ]));
    animation.start();
    return () => animation.stop();
  }, [screen, status, pulse]);

  useEffect(() => {
    checkConnection();
  },[]);

  useEffect(() => {
    if (screen === 'voice') startListening();
    return () => { void stopRecordingOnly(); };
    // Voice session begins once when the assistant screen opens.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [screen]);

  useEffect(() => {
    if (!recorderState.isRecording || closing.current) return;
    const meter = recorderState.metering ?? -160;
    const talking = meter > -42;
    if (talking) {
      heardSpeech.current = true;
      quietSince.current = null;
      setStatus('listening');
      Animated.timing(level, { toValue: 1.12, duration: 160, useNativeDriver: true }).start();
    } else {
      Animated.timing(level, { toValue: 0.94, duration: 380, useNativeDriver: true }).start();
      if (heardSpeech.current) {
        quietSince.current ??= Date.now();
        if (Date.now() - quietSince.current > 1600) void finishListening(recorder);
      }
    }
  }, [recorder, recorderState, level]);

  const checkConnection = async () =>{
    const healthUrl = `${API_BASE_URL}/api/health`
    const response = await fetch(healthUrl,{
      method: 'GET',
      headers:{
        'Content-Type': 'application/json',
      }
    });
    if(response?.status){
        console.log("Connected");
        return;
    }
    console.log("Not connected");
  };

  const startListening = async () => {
    try {
      setError('');
      setStatus('starting');
      const permission = await requestRecordingPermissionsAsync();
      if (!permission.granted) throw new Error('Microphone access is needed to ask a voice question.');
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
      await recorder.prepareToRecordAsync();
      recorder.record();
      setRecording(recorder);
      setStatus('listening');
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Could not start the microphone.';
      setError(message);
      setStatus('stopped');
    }
  };

  const stopRecordingOnly = async () => {
    const active = recording ?? recorder;
    try {
      if (active.isRecording) await active.stop();
    } catch { /* The recorder may already have been closed by the silence timer. */ }
  };

  const finishListening = async (active = recording) => {
    if (closing.current || !active) return;
    closing.current = true;
    setStatus('sending');
    try {
      if (active.isRecording) await active.stop();
      const uri = active.uri;
      setRecording(null);
      await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true });
      if (uri) {
        const form = new FormData();
        const audioFile = new File(uri);
        form.append('file', audioFile);
        const response = await fetch(`${API_BASE_URL}/api/transcribe`, { method: 'POST', body: form });
        if (!response.ok) throw new Error(`Transcription request failed (${response.status}).`);
      }
      setStatus('stopped');
      setTimeout(() => setScreen('home'), 450);
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Could not send your voice question.';
      setError(message);
      setStatus('stopped');
    }
  };

  const openVoice = () => {
    closing.current = false;
    quietSince.current = null;
    heardSpeech.current = false;
    setScreen('voice');
  };

  if (screen === 'voice') {
    const voiceTitle = status === 'starting' ? 'Getting ready' : status === 'sending' ? 'Thinking' : status === 'stopped' ? 'Voice conversation closed' : 'Listening';
    const voiceHint = error || (status === 'starting' ? 'Preparing your microphone' : status === 'sending' ? 'Understanding what you said' : status === 'stopped' ? 'Your microphone and audio have been disconnected.' : 'Go ahead, I’m listening');
    return (
      <SafeAreaView style={styles.voicePage}>
        <StatusBar barStyle="dark-content" />
        <View style={styles.voiceTopBar}>
          <Pressable accessibilityLabel="Close voice assistant" onPress={() => { closing.current = true; void stopRecordingOnly(); setScreen('home'); }} style={styles.voiceIconButton}>
            <Text style={styles.closeGlyph}>×</Text>
          </Pressable>
          <View style={styles.voiceHeading}>
            <View style={styles.liveDot} />
            <Text style={styles.voiceConversationTitle}>Voice conversation</Text>
          </View>
          <View style={styles.voiceIconButton} />
        </View>
        <View style={styles.orbStage}>
          <Orb pulse={pulse} level={level} active={status === 'listening'} sending={status === 'sending'} />
        </View>
        <View style={styles.voiceFooter}>
          {status === 'stopped' ? (
            <View style={styles.endedCopy}>
              <Text style={styles.endedEyebrow}>SESSION ENDED</Text>
              <Text style={styles.voiceTitle}>{voiceTitle}</Text>
              <Text style={styles.voiceHint}>{voiceHint}</Text>
              <Pressable style={styles.restartButton} onPress={openVoice}>
                <Text style={styles.restartButtonText}>Start another conversation</Text>
              </Pressable>
            </View>
          ) : (
            <>
              <View style={styles.statusLine}>
                {status === 'sending' ? <ActivityIndicator color="#5679DC" size="small" /> : <View style={styles.statusPulse} />}
                <Text style={styles.voiceTitle}>{voiceTitle}</Text>
              </View>
              <Text style={styles.voiceHint}>{voiceHint}</Text>
              <View style={styles.voiceControls}>
                <View style={styles.controlItem}>
                  <View style={styles.controlCircle}>
                    <Text style={styles.micGlyph}>♩</Text>
                  </View>
                  <Text style={styles.controlLabel}>Mic active</Text>
                </View>
                <Pressable style={styles.controlItem} onPress={() => { closing.current = true; void stopRecordingOnly(); setScreen('home'); }}>
                  <View style={styles.endControlCircle}>
                    <Text style={styles.endGlyph}>×</Text>
                  </View>
                  <Text style={styles.controlLabel}>End voice</Text>
                </Pressable>
              </View>
            </>
          )}
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.page}>
      <StatusBar barStyle="dark-content" />
      <ScrollView contentContainerStyle={styles.homeContent} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <View><Text style={styles.eyebrow}>CURRENT LOCATION</Text><Text style={styles.location}>Netherlands <Text style={styles.chevron}>⌄</Text></Text></View>
          <View style={styles.avatar}><Text style={styles.avatarText}>W</Text></View>
        </View>
        <View style={styles.search}><Text style={styles.searchIcon}>⌕</Text><Text style={styles.searchText}>Search destinations, activities…</Text><Text style={styles.filterIcon}>☷</Text></View>
        <View style={styles.sectionHeading}><View><Text style={styles.eyebrow}>MAKE ROOM FOR WONDER</Text><Text style={styles.sectionTitle}>Select your next trip</Text></View><Text style={styles.seeAll}>See all</Text></View>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
          {['🌏  Asia', '🌍  Europe', '🌎  America', '✦  All'].map((item, i) => <View key={item} style={[styles.chip, i === 0 && styles.activeChip]}><Text style={[styles.chipText, i === 0 && styles.activeChipText]}>{item}</Text></View>)}
        </ScrollView>
        <ScrollView horizontal pagingEnabled={false} showsHorizontalScrollIndicator={false} contentContainerStyle={styles.cards}>
          {trips.map((trip, i) => <View key={trip.title} style={[styles.tripCard, i > 0 && { marginLeft: 14 }]}>
            <View style={[styles.cardSky, { backgroundColor: trip.colors[0] }]}><View style={[styles.sun, { backgroundColor: i === 0 ? '#FFD19D' : '#FFF0C7' }]} /><View style={[styles.mountainBack, { borderBottomColor: trip.colors[1] }]} /><View style={[styles.mountainFront, { borderBottomColor: trip.colors[2] }]} /><View style={styles.cardPlace}><Text style={styles.cardPlaceText}>{trip.place}</Text></View></View>
            <View style={styles.cardShade} />
            <View style={styles.rating}><Text style={styles.star}>★</Text><Text style={styles.ratingText}>5.0</Text></View>
            <View style={styles.cardCopy}><Text style={styles.cardTitle}>{trip.title}</Text><Text style={styles.cardSubtitle}>{trip.subtitle}</Text></View>
            <Pressable onPress={openVoice} style={styles.cardArrow}><Text style={styles.arrowText}>↗</Text></Pressable>
          </View>)}
        </ScrollView>
        <View style={styles.sectionHeading}><View><Text style={styles.eyebrow}>CURATED FOR YOU</Text><Text style={styles.sectionTitle}>A little inspiration</Text></View></View>
        <View style={styles.inspiration}><Text style={styles.inspirationIcon}>✧</Text><View style={{ flex: 1 }}><Text style={styles.inspirationTitle}>Find your kind of getaway</Text><Text style={styles.inspirationText}>Slow mornings, new places, and a plan that feels like yours.</Text></View><Text style={styles.inspirationArrow}>›</Text></View>
      </ScrollView>
      <View style={styles.bottomBar}>
        <View style={styles.navActive}><Text style={styles.navGlyph}>⌂</Text><Text style={styles.navActiveText}>Home</Text></View>
        <Text style={styles.navGlyph}>♡</Text><Text style={styles.navGlyph}>▤</Text><Text style={styles.navGlyph}>♙</Text>
      </View>
      <Pressable accessibilityRole="button" onPress={openVoice} style={styles.askButton}>
        <Text style={styles.askOrb}>✦</Text><Text style={styles.askText}>Ask AI</Text><Text style={styles.askArrow}>↗</Text>
      </Pressable>
    </SafeAreaView>
  );
}

function Orb({ pulse, level, active, sending }: { pulse: Animated.Value; level: Animated.Value; active: boolean; sending: boolean }) {
  const flowShift = level.interpolate({ inputRange: [0.94, 1.12], outputRange: [-9, 9] });
  const cyanShift = level.interpolate({ inputRange: [0.94, 1.12], outputRange: [8, -8] });

  return <Animated.View style={[styles.orbWrap, { transform: [{ scale: Animated.multiply(pulse, level) }] }]}>
    <View style={[styles.orbHalo, (active || sending) && styles.orbHaloActive]} />
    <View style={styles.orbBody}>
      <LinearGradient
        colors={['#FBFDFF', '#C9DCFF', '#6288EE', '#3459CC']}
        locations={[0, 0.38, 0.72, 1]}
        start={{ x: 0.22, y: 0.12 }}
        end={{ x: 0.85, y: 0.95 }}
        style={styles.orbBase}
      />
      <Animated.View style={[styles.orbWhiteMist, { transform: [{ translateX: flowShift }, { scale: level }] }]}>
        <LinearGradient
          colors={['rgba(245,250,255,.92)', 'rgba(255,255,255,.5)', 'rgba(255,255,255,0)']}
          locations={[0, 0.42, 1]}
          start={{ x: 0.2, y: 0.1 }}
          end={{ x: 0.8, y: 0.9 }}
          style={StyleSheet.absoluteFill}
        />
      </Animated.View>
      <Animated.View style={[styles.orbCyanFlow, { transform: [{ translateX: cyanShift }, { scaleY: level }] }]}>
        <LinearGradient
          colors={['rgba(101,142,255,.05)', 'rgba(101,142,255,.7)', 'rgba(52,89,204,.08)']}
          locations={[0, 0.5, 1]}
          start={{ x: 0.7, y: 0 }}
          end={{ x: 0.3, y: 1 }}
          style={StyleSheet.absoluteFill}
        />
      </Animated.View>
      <Animated.View style={[styles.orbTopBloom, { opacity: active ? 0.95 : 0.72, transform: [{ translateX: flowShift }] }]}>
        <LinearGradient
          colors={['rgba(255,255,255,.48)', 'rgba(255,255,255,0)']}
          start={{ x: 0.15, y: 0.1 }}
          end={{ x: 0.9, y: 0.8 }}
          style={StyleSheet.absoluteFill}
        />
      </Animated.View>
      <BlurView intensity={active || sending ? 18 : 12} tint="light" style={styles.orbBlur} />
    </View>
  </Animated.View>;
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: '#F7F7F9' }, homeContent: { paddingHorizontal: 22, paddingTop: 15, paddingBottom: 130 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 },
  eyebrow: { color: '#9399A5', fontSize: 11, fontWeight: '700', letterSpacing: 1.05 }, location: { color: '#24262B', fontSize: 26, fontWeight: '700', marginTop: 5, letterSpacing: -0.7 }, chevron: { color: '#44474F', fontSize: 23 }, avatar: { width: 44, height: 44, backgroundColor: '#EEE6FF', borderRadius: 22, alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: '#FFF' }, avatarText: { color: '#7C60DB', fontWeight: '700', fontSize: 16 },
  search: { height: 58, borderRadius: 19, backgroundColor: '#FFF', borderColor: '#E7E6EB', borderWidth: 1, flexDirection: 'row', alignItems: 'center', paddingHorizontal: 17, marginBottom: 31 }, searchIcon: { fontSize: 28, color: '#282A30', marginRight: 12 }, searchText: { color: '#969BA5', flex: 1, fontSize: 14 }, filterIcon: { fontSize: 23, color: '#45474D' },
  sectionHeading: { flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 17 }, sectionTitle: { fontSize: 22, fontWeight: '700', color: '#27292E', marginTop: 5, letterSpacing: -0.5 }, seeAll: { color: '#8D71E9', fontWeight: '600', marginBottom: 3 },
  chips: { paddingBottom: 22, gap: 9 }, chip: { borderRadius: 22, borderWidth: 1, borderColor: '#E3E2E8', paddingHorizontal: 16, height: 42, justifyContent: 'center', backgroundColor: '#FFF' }, activeChip: { backgroundColor: '#EEC4F5', borderColor: '#EEC4F5' }, chipText: { fontSize: 13, color: '#464850', fontWeight: '500' }, activeChipText: { color: '#3E3446' },
  cards: { paddingBottom: 34, paddingRight: 22 }, tripCard: { width: 274, height: 372, borderRadius: 27, overflow: 'hidden', backgroundColor: '#274B57' }, cardSky: { ...StyleSheet.absoluteFill }, sun: { width: 92, height: 92, borderRadius: 50, position: 'absolute', top: 66, right: 41, opacity: 0.85 }, mountainBack: { position: 'absolute', bottom: 72, left: -10, width: 310, height: 195, borderLeftWidth: 155, borderRightWidth: 155, borderBottomWidth: 178, borderLeftColor: 'transparent', borderRightColor: 'transparent', opacity: 0.9 }, mountainFront: { position: 'absolute', bottom: 45, left: -22, width: 340, height: 155, borderLeftWidth: 170, borderRightWidth: 170, borderBottomWidth: 138, borderLeftColor: 'transparent', borderRightColor: 'transparent', opacity: 0.94 }, cardPlace: { position: 'absolute', top: 22, left: 20, paddingHorizontal: 11, paddingVertical: 7, borderRadius: 20, backgroundColor: 'rgba(255,255,255,0.22)' }, cardPlaceText: { fontSize: 10, color: '#FFF', fontWeight: '700', letterSpacing: 1.3 }, cardShade: { ...StyleSheet.absoluteFill, backgroundColor: 'rgba(10,18,26,0.18)' }, rating: { position: 'absolute', top: 19, right: 18, borderRadius: 18, paddingHorizontal: 10, height: 32, flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(28,30,34,0.45)', gap: 5 }, star: { color: '#F6C4FB', fontSize: 13 }, ratingText: { color: '#FFF', fontSize: 12, fontWeight: '600' }, cardCopy: { position: 'absolute', bottom: 23, left: 21, right: 65 }, cardTitle: { color: '#FFF', fontSize: 22, lineHeight: 26, fontWeight: '700' }, cardSubtitle: { color: 'rgba(255,255,255,.88)', fontSize: 12, lineHeight: 17, marginTop: 8 }, cardArrow: { width: 48, height: 48, borderRadius: 25, backgroundColor: '#F2C5F8', position: 'absolute', bottom: 22, right: 18, alignItems: 'center', justifyContent: 'center' }, arrowText: { color: '#292631', fontSize: 24 },
  inspiration: { flexDirection: 'row', alignItems: 'center', borderRadius: 20, padding: 17, backgroundColor: '#FFF', borderColor: '#ECEAF0', borderWidth: 1 }, inspirationIcon: { width: 42, height: 42, borderRadius: 14, backgroundColor: '#F4E4F8', color: '#A356B8', textAlign: 'center', textAlignVertical: 'center', fontSize: 24, marginRight: 12, overflow: 'hidden' }, inspirationTitle: { color: '#292B31', fontWeight: '700', fontSize: 14 }, inspirationText: { color: '#888D98', fontSize: 12, lineHeight: 17, marginTop: 4 }, inspirationArrow: { fontSize: 26, color: '#9B8BCB', marginLeft: 8 },
  bottomBar: { position: 'absolute', left: 22, right: 22, bottom: 17, height: 70, borderRadius: 35, backgroundColor: '#202326', flexDirection: 'row', justifyContent: 'space-around', alignItems: 'center', paddingHorizontal: 10 }, navActive: { height: 46, paddingHorizontal: 17, borderRadius: 24, backgroundColor: '#FFF', flexDirection: 'row', alignItems: 'center', gap: 7 }, navGlyph: { color: '#F8F8FA', fontSize: 23 }, navActiveText: { color: '#25272B', fontSize: 13, fontWeight: '600' },
  askButton: { position: 'absolute', right: 28, bottom: 103, height: 58, borderRadius: 30, paddingHorizontal: 17, flexDirection: 'row', alignItems: 'center', gap: 9, backgroundColor: '#FFF', borderWidth: 1, borderColor: '#E8D8F4', elevation: 5, shadowColor: '#81718D', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.16, shadowRadius: 12 }, askOrb: { fontSize: 18, color: '#9A73F0', textShadowColor: '#83D9FA', textShadowRadius: 7 }, askText: { color: '#24252A', fontWeight: '600', fontSize: 15 }, askArrow: { color: '#8870D7', fontSize: 18, marginLeft: 1 },
  voicePage: { flex: 1, backgroundColor: '#FAFBFE', alignItems: 'center' }, voiceTopBar: { width: '100%', flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 20, paddingTop: 10 }, voiceIconButton: { width: 42, height: 42, borderRadius: 22, borderWidth: 1, borderColor: 'rgba(36,50,80,.08)', backgroundColor: 'rgba(255,255,255,.75)', alignItems: 'center', justifyContent: 'center' }, closeGlyph: { fontSize: 27, color: '#536078', lineHeight: 30, fontWeight: '300' }, voiceHeading: { flexDirection: 'row', alignItems: 'center', gap: 8 }, liveDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: '#6383DE', shadowColor: '#6383DE', shadowRadius: 5, shadowOpacity: 0.35 }, voiceConversationTitle: { color: '#677185', fontSize: 13, fontWeight: '500' }, orbStage: { flex: 1, width: '100%', alignItems: 'center', justifyContent: 'center', paddingTop: 12 },
  orbWrap: { width: 324, height: 324, alignItems: 'center', justifyContent: 'center' }, orbHalo: { position: 'absolute', width: 288, height: 288, borderRadius: 144, backgroundColor: 'rgba(74,112,219,.13)', shadowColor: '#4A70DB', shadowRadius: 38, shadowOpacity: 0.24, shadowOffset: { width: 0, height: 0 } }, orbHaloActive: { shadowColor: '#5679DC', shadowOpacity: 0.48, shadowRadius: 48 }, orbBody: { width: 252, height: 252, borderRadius: 126, overflow: 'hidden', backgroundColor: '#3459CC', alignItems: 'center', justifyContent: 'center', shadowColor: '#3459CC', shadowRadius: 20, shadowOpacity: 0.28, shadowOffset: { width: 0, height: 5 }, elevation: 10 }, orbBase: { ...StyleSheet.absoluteFill, backgroundColor: '#3459CC' }, orbWhiteMist: { position: 'absolute', top: -18, left: -15, width: 280, height: 182, borderRadius: 140 }, orbCyanFlow: { position: 'absolute', top: -20, left: 78, width: 125, height: 250, borderRadius: 70, opacity: 0.9 }, orbTopBloom: { position: 'absolute', top: -10, left: 20, width: 215, height: 145, borderRadius: 115, opacity: 0.9 }, orbBlur: { ...StyleSheet.absoluteFill }, voiceFooter: { alignItems: 'center', width: '100%', paddingHorizontal: 28, paddingBottom: 25, minHeight: 205 }, statusLine: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 9 }, statusPulse: { width: 7, height: 7, borderRadius: 4, backgroundColor: '#5679DC' }, voiceTitle: { fontSize: 21, fontWeight: '500', color: '#1D273D', letterSpacing: -0.5 }, voiceHint: { minHeight: 42, textAlign: 'center', color: '#8B94A6', fontSize: 14, lineHeight: 20, marginTop: 7 }, voiceControls: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'center', gap: 62, marginTop: 5 }, controlItem: { width: 82, alignItems: 'center', gap: 8 }, controlCircle: { width: 58, height: 58, borderRadius: 29, borderWidth: 1, borderColor: 'rgba(26,39,69,.09)', backgroundColor: 'rgba(255,255,255,.9)', alignItems: 'center', justifyContent: 'center', shadowColor: '#2F4069', shadowRadius: 11, shadowOpacity: 0.1, shadowOffset: { width: 0, height: 5 } }, micGlyph: { color: '#496ED5', fontSize: 27, transform: [{ rotate: '90deg' }] }, controlLabel: { color: '#657086', fontSize: 12, fontWeight: '500' }, endControlCircle: { width: 58, height: 58, borderRadius: 29, backgroundColor: '#141B2A', alignItems: 'center', justifyContent: 'center', shadowColor: '#0D1526', shadowRadius: 12, shadowOpacity: 0.2, shadowOffset: { width: 0, height: 6 } }, endGlyph: { color: '#FFF', fontSize: 27, lineHeight: 29, fontWeight: '300' }, endedCopy: { alignItems: 'center', maxWidth: 420 }, endedEyebrow: { color: '#8791A4', fontSize: 10, fontWeight: '700', letterSpacing: 1.2 }, restartButton: { marginTop: 18, paddingHorizontal: 18, paddingVertical: 11, borderRadius: 22, borderWidth: 1, borderColor: '#DCE1EA', backgroundColor: '#FFF' }, restartButtonText: { color: '#3F4C64', fontSize: 13, fontWeight: '500' },
});
