import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslateModule } from '@ngx-translate/core';
import { ApiService, BotSession } from '../../services/api.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, TranslateModule],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss'
})
export class DashboardComponent implements OnInit {
  session: BotSession | null = null;
  status = 'idle';

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getBotStatus().subscribe((s: any) => {
      if (s.stats) {
        this.session = s as BotSession;
        this.status = s.status;
      } else {
        this.status = s.status ?? 'idle';
      }
    });
  }
}
