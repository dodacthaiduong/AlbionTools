import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslateModule } from '@ngx-translate/core';
import { Subscription } from 'rxjs';
import { ApiService, BotSession } from '../../services/api.service';
import { WebsocketService } from '../../services/websocket.service';

@Component({
  selector: 'app-bot-status',
  standalone: true,
  imports: [CommonModule, TranslateModule],
  templateUrl: './bot-status.component.html',
  styleUrl: './bot-status.component.scss'
})
export class BotStatusComponent implements OnInit, OnDestroy {
  session: BotSession | null = null;
  status = 'idle';
  private sub?: Subscription;

  constructor(private api: ApiService, private ws: WebsocketService) {}

  ngOnInit(): void {
    this.refresh();
    this.ws.connect();
    this.sub = this.ws.messages$.subscribe(msg => {
      if (msg.event === 'session_update') {
        this.session = msg.data as BotSession;
        this.status = this.session.status;
      }
    });
  }

  refresh(): void {
    this.api.getBotStatus().subscribe((s: any) => {
      if (s.stats) {
        this.session = s as BotSession;
        this.status = s.status;
      } else {
        this.status = s.status ?? 'idle';
      }
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }
}
