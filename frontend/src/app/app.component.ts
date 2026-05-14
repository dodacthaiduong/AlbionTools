import { Component } from '@angular/core';
import { NavComponent } from './shell/nav/nav.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [NavComponent],
  template: '<app-nav></app-nav>',
  styleUrl: './app.component.scss'
})
export class AppComponent {}
