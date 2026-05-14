import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslateModule } from '@ngx-translate/core';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { ApiService, Transaction } from '../../services/api.service';

@Component({
  selector: 'app-transactions',
  standalone: true,
  imports: [CommonModule, TranslateModule, MatTableModule, MatButtonModule],
  templateUrl: './transactions.component.html',
  styleUrl: './transactions.component.scss'
})
export class TransactionsComponent implements OnInit {
  transactions: Transaction[] = [];
  total = 0;
  displayedColumns = ['timestamp', 'item', 'tier', 'quantity', 'unit_price', 'total_price', 'market_city'];

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getTransactions(50, 0).subscribe(r => {
      this.transactions = r.data ?? [];
      this.total = r.total ?? 0;
    });
  }

  exportCsv(): void {
    window.open(this.api.getExportUrl(), '_blank');
  }
}
