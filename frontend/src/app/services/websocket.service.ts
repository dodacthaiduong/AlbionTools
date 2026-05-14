import { Injectable, OnDestroy } from '@angular/core';
import { Subject } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class WebsocketService implements OnDestroy {
  private ws: WebSocket | null = null;
  messages$ = new Subject<{ event: string; data: unknown }>();

  connect(url = 'ws://localhost:8080/ws'): void {
    if (this.ws) return;
    this.ws = new WebSocket(url);
    this.ws.onmessage = (e) => {
      try { this.messages$.next(JSON.parse(e.data)); } catch {}
    };
    this.ws.onclose = () => { this.ws = null; };
  }

  disconnect(): void {
    this.ws?.close();
    this.ws = null;
  }

  ngOnDestroy(): void {
    this.disconnect();
  }
}
