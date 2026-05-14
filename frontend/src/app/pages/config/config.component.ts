import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { MatTableModule } from '@angular/material/table';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ApiService, ItemConfig } from '../../services/api.service';

@Component({
  selector: 'app-config',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslateModule, MatTableModule, MatInputModule, MatButtonModule, MatSnackBarModule],
  templateUrl: './config.component.html',
  styleUrl: './config.component.scss'
})
export class ConfigComponent implements OnInit {
  items: ItemConfig[] = [];
  displayedColumns = ['full_name', 'tier', 'estimated_price', 'min_sell_price', 'actions'];
  editPrices: Record<string, number | null> = {};

  constructor(private api: ApiService, private snack: MatSnackBar) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.api.getItemConfigs().subscribe(r => {
      this.items = r.data ?? [];
      this.items.forEach(i => { this.editPrices[i.id] = i.min_sell_price; });
    });
  }

  save(item: ItemConfig): void {
    const price = this.editPrices[item.id] ?? null;
    this.api.updateMinSellPrice(item.id, price).subscribe(() => {
      this.snack.open('Saved', undefined, { duration: 2000 });
      item.min_sell_price = price;
    });
  }
}
